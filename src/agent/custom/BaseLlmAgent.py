import json
import os
import pprint
from typing import Any, Union
import re
from enum import Enum

from openai import OpenAI
from rich.console import Console

from src.agent.Agent import Agent
from src.agent.custom.BaseLlmAgentPrompts import BaseLlmAgentPrompts
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player

class AgentType(Enum):
    DEEPSEEK = 0

class BaseLlmAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        self.console = Console(force_terminal=True)
        self.client = self.init_agent()
        self.prompts = BaseLlmAgentPrompts()
        self.system_prompt = self.prompts.system_prompt
        self.chat_context = [
            {"role": "system", "content": self.system_prompt}
        ]
        self._errors = 0
        super().__init__(agent_name, config, player, game, shared_memory)
        self.MAX_CONTEXT_LEN = self.agent_config["context_len"]

    @staticmethod
    def init_agent(agent_type: AgentType = AgentType.DEEPSEEK):
        client = None
        match agent_type:
            case AgentType.DEEPSEEK:
                deepseek_api_key = os.getenv('DEEPSEEK_KEY', "empty")
                if deepseek_api_key == "empty":
                    raise Exception("Add api key to env variable DEEPSEEK_KEY")
                client = OpenAI(
                    api_key= deepseek_api_key,
                    base_url="https://api.deepseek.com"
                )
        return client

    def ask_llm(self, prompt: dict[str, str], so_answer_field_name: Union[str, None] = "result") -> str:
        self.trim_chat_context()
        answer, json_objects, errors = self.generate_answer(prompt)
        while (errors
            or (not json_objects and so_answer_field_name)
            or (json_objects and so_answer_field_name and not json_objects[0].get(so_answer_field_name))):

            prompt = {"prompt": self.prompts.get_regenerate_prompt(so_answer_field_name, errors)}
            answer, json_objects, errors = self.generate_answer(prompt, regenerate=True)

        json_object = json_objects[0]
        users_role = json_object.get("users_role")
        if users_role:
            self.local_log.append({"content": answer, "users_role": users_role})
            self.console.print(f"[green]Assumptions about the role:[/green]", style="bold")
            pprint.pprint(users_role)
        else:
            self.local_log.append({"content": answer})

        result = json_object.get(so_answer_field_name) if so_answer_field_name else answer
        self.console.print(f"[green]LLM answer:[/green] \n{result}", style="bold")
        return result

    def generate_answer(self, prompt: dict[str, str], regenerate: bool = False):
        prompt = prompt['prompt']
        self.console.print(f"[blue] Prompt: \n{prompt} [/blue]", style="bold")
        self.local_log.append({"content": prompt})
        self.chat_context.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model="deepseek-chat",  # deepseek-reasoner или deepseek-chat
            messages=self.chat_context,
            temperature=0.7,
            max_tokens=700,
            stream=False
        )

        answer = response.choices[0].message.content
        print("Raw answer: ")
        pprint.pprint(answer)

        self.chat_context.append({"role": "assistant", "content": answer})
        self.local_log.append({"content": answer})

        json_objects, errors = self.extract_json_objects(row_text=answer)
        return answer, json_objects, errors

    def trim_chat_context(self):
        if len(self.chat_context) > self.MAX_CONTEXT_LEN:
            print("===" * 30)
            print("Trim chat context")
            print("===" * 30)
            old_context = self.chat_context[-self.MAX_CONTEXT_LEN:]
            self.chat_context = [
                {"role": "system", "content": self.system_prompt}
            ]
            self.chat_context.extend(old_context)

    def extract_json_objects(self, row_text: str):
        errors = []
        json_objects = []
        pattern = r'```json\n(.*?)\n```'
        matches = re.finditer(pattern, row_text, re.DOTALL)

        for match in matches:
            json_str = match.group(1)
            try:
                json_object = json.loads(json_str)
                json_objects.append(json_object)
                self.console.print(f"[green]Parsed JSON:[/green]", style="bold")
                pprint.pprint(json_object)
                print("===" * 30)
            except json.JSONDecodeError as e:
                self.local_log.append({"content": row_text, "error": e})
                self.console.print(f"[red]ERROR:[/red] JSON parsing error in block: {e}", style="bold")
                errors.append(str(e))
        return json_objects, errors

    def base_card_for_discard(self, num_cards: int) -> str:
        discarded = []
        for i in range(num_cards):
            discarded.append(self.player_hand[i].card_id.value)
        return " ".join(discarded)

    def choice_card_for_play(self) -> str:
        self._errors = 0
        game_state = self.get_game_state()
        prompt = self.prompts.choice_card_for_play_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_opponent(self, card: Card) -> str:
        opponents = [player for player in self.game.get_player_names() if player != self.name]
        game_state = {"card": card, "opponents": opponents}
        prompt = self.prompts.get_opponent_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_action_type(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        game_state = {"card": card, "opponent": opponent}
        prompt = self.prompts.get_action_type_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_card_for_steal(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        action_type = options["action_type"]
        game_state = {"card": card, "opponent": opponent, "action_type": action_type}
        prompt = self.prompts.get_card_for_steal_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_indians_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_indians_response_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_bang_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_bang_response_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_gatling_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_gatling_response_prompt(game_state=game_state)
        return self.ask_llm(prompt)

    def get_card_for_discard(self, num_cards: int) -> str:
        if self._errors < 3:
            game_state = {"num_cards": num_cards, "cur_state": self.__get_player_current_state()}
            prompt = self.prompts.get_card_for_discard_prompt(game_state=game_state)
            return self.ask_llm(prompt)
        else:
            return self.base_card_for_discard(num_cards)

    def react_to_discard_error(self, errors: str):
        game_state = {"errors": errors, "cur_state": self.__get_player_current_state()}
        prompt = self.prompts.react_to_discard_error_prompt(game_state=game_state)
        self.ask_llm(prompt, so_answer_field_name=None)
        self.console.print(f"[red]ERROR:[/red] ERROR ON DISCARD", style="bold")
        self._errors += 1

