import json
import pprint
from typing import Any, Union
import re

from rich.console import Console

from src.agent.Agent import Agent, init_agent
from src.agent.custom.BaseMultiLlmAgentPrompts import BaseMultiLlmAgentPrompts
from src.emulator.Emulator import LogEventType
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player


class BaseMultiLlmAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        self.console = Console(force_terminal=True)
        self.client = init_agent()
        self.prompts = BaseMultiLlmAgentPrompts()
        self.chat_context = []
        self.agents = {"player": {"system_prompt": self.prompts.player_prompt},
                       "role_finder": {"system_prompt": self.prompts.role_finder_prompt},
                       "log_analyzer": {"system_prompt": self.prompts.log_analyzer_prompt},
                       "summarizer": {"system_prompt": self.prompts.summarizer_prompt}, }
        self._errors = 0
        super().__init__(agent_name, config, player, game, shared_memory)
        self.agents_map = self.agent_config['agents_map']
        self.MAX_CONTEXT_LEN = self.agent_config["context_len"]
        self.base_gen_conf = self.agent_config["base_gen_conf"]

    @staticmethod
    def base_agents_list() -> list:
        return ["summarizer"]

    def ask_llm(self, prompt: str, agents: list, so_answer_field_name: Union[str, None] = "result") -> str:
        if not agents:
            agents = self.base_agents_list()
        answer, json_objects, errors = self.generate_answer(prompt, agents=agents)
        while (errors
               or (not json_objects and so_answer_field_name)
               or (json_objects and so_answer_field_name and not json_objects[0].get(so_answer_field_name))):
            prompt = {"prompt": self.prompts.get_regenerate_prompt(so_answer_field_name, errors)}
            answer, json_objects, errors = self.generate_answer(prompt, regenerate=True)

        json_object = json_objects[0]
        users_role = json_object.get("users_role")
        say_to_all = json_object.get("say_to_all")
        if users_role:
            self.local_log.append({"content": answer, "users_role": users_role})
            self.console.print(f"[green]Assumptions about the role:[/green]", style="bold")
            pprint.pprint(users_role)
        else:
            self.local_log.append({"content": answer})
        if say_to_all:
            self.shared_memory.append({"type": LogEventType.PLAYER_SAY,
                                       "value": {"player": self.name, "say": say_to_all}})
            self.console.print(f"[green]Say to all:[/green]", style="bold")
            pprint.pprint(say_to_all)

        result = json_object.get(so_answer_field_name) if so_answer_field_name else answer
        self.console.print(f"[green]LLM answer:[/green] \n{result}", style="bold")
        return result

    def generate_answer(self, prompt: dict[str, str], agents: Union[list, None] = None, regenerate: bool = False):
        task_context = []
        state = prompt.get('state', '')
        prompt = prompt.get('prompt', '')
        answer = ""
        prompt_pos = 0

        self.trim_chat_context()
        if state:
            add_to_context = state
        else:
            add_to_context = prompt
            prompt_pos = len(task_context)
        self.console.print(f"[blue] Prompt: \n{add_to_context} [/blue]", style="bold")
        self.local_log.append({"content": add_to_context})
        task_context.append({"role": "user", "content": add_to_context})
        if regenerate:
            agents = ["summarizer"]
        for pos, agent in enumerate(agents):
            if state and pos == len(agents) - 1:
                self.console.print(f"[blue] Prompt: \n{prompt} [/blue]", style="bold")
                self.local_log.append({"content": prompt})
                prompt_pos = len(task_context)
                task_context.append({"role": "user", "content": prompt})

            if regenerate:
                all_context = self.chat_context + task_context
            else:
                system_prompt = [{"role": "system", "content": self.agents[agent]['system_prompt']}]
                all_context = system_prompt + self.chat_context + task_context

            answer = self.llm_api_call(all_context, self.base_gen_conf)

            print("===" * 30)
            print(f"Agent name: {agent}")
            print("Raw answer: ")
            print(answer)

            self.local_log.append({"content": answer, "agent": agent})
            task_context.append({"role": "assistant", "content": answer})

        task_context.pop(prompt_pos)
        self.chat_context.extend(task_context)

        json_objects, errors = self.extract_json_objects(row_text=answer)
        return answer, json_objects, errors

    def llm_api_call(self, messages, gen_config: dict[str, Any]) -> str:
        response = self.client.chat.completions.create(
            model=gen_config["model"],
            messages=messages,
            temperature=gen_config["temperature"],
            max_tokens=gen_config["max_tokens"],
            stream=False
        )

        return response.choices[0].message.content

    def trim_chat_context(self):
        if len(self.chat_context) > self.MAX_CONTEXT_LEN:
            print("===" * 30)
            print("Trim chat context")
            print("===" * 30)
            self.chat_context = self.chat_context[-self.MAX_CONTEXT_LEN:]


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
        agents = self.agents_map.get('choice_card_for_play', [])
        return self.ask_llm(prompt, agents=agents)

    def get_opponent(self, card: Card) -> str:
        opponents = [player for player in self.game.get_player_names() if player != self.name]
        game_state = {"card": card, "opponents": opponents}
        prompt = self.prompts.get_opponent_prompt(game_state=game_state)
        agents = self.agents_map.get('get_opponent', [])
        return self.ask_llm(prompt, agents=agents)

    def get_action_type(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        game_state = {"card": card, "opponent": opponent}
        prompt = self.prompts.get_action_type_prompt(game_state=game_state)
        agents = self.agents_map.get('get_action_type', [])
        return self.ask_llm(prompt, agents=agents)

    def get_card_for_steal(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        action_type = options["action_type"]
        game_state = {"card": card, "opponent": opponent, "action_type": action_type}
        prompt = self.prompts.get_card_for_steal_prompt(game_state=game_state)
        agents = self.agents_map.get('get_card_for_steal', [])
        return self.ask_llm(prompt, agents=agents)

    def get_indians_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_indians_response_prompt(game_state=game_state)
        agents = self.agents_map.get('get_indians_response', [])
        return self.ask_llm(prompt, agents=agents)

    def get_bang_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_bang_response_prompt(game_state=game_state)
        agents = self.agents_map.get('get_bang_response', [])
        return self.ask_llm(prompt, agents=agents)

    def get_gatling_response(self) -> str:
        game_state = self.get_game_state()
        prompt = self.prompts.get_gatling_response_prompt(game_state=game_state)
        agents = self.agents_map.get('get_gatling_response', [])
        return self.ask_llm(prompt, agents=agents)

    def get_card_for_discard(self, num_cards: int) -> str:
        if self._errors < 3:
            game_state = {"num_cards": num_cards, "cur_state": self.__get_player_current_state()}
            prompt = self.prompts.get_card_for_discard_prompt(game_state=game_state)
            agents = self.agents_map.get('get_card_for_discard', [])
            return self.ask_llm(prompt, agents=agents)
        else:
            return self.base_card_for_discard(num_cards)

    def react_to_discard_error(self, errors: str):
        game_state = {"errors": errors, "cur_state": self.__get_player_current_state()}
        prompt = self.prompts.react_to_discard_error_prompt(game_state=game_state)
        agents = self.agents_map.get('react_to_discard_error', [])
        self.ask_llm(prompt, agents=agents, so_answer_field_name=None)
        self.console.print(f"[red]ERROR:[/red] ERROR ON DISCARD", style="bold")
        self._errors += 1


