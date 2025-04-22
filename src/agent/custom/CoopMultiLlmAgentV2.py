import pprint
import re
from typing import Any, Union

from src.agent.custom.BaseMultiLlmAgent import BaseMultiLlmAgent
from src.agent.custom.CoopMultiLlmAgentV2Prompts import CoopMultiLlmAgentV2Prompts
from src.emulator.Emulator import LogEventType
from src.emulator.LoggedList import LoggedList
from src.game.Game import Game
from src.game.Player import Player

class CoopMultiLlmAgentV2(BaseMultiLlmAgent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):

        super().__init__(agent_name, config, player, game, shared_memory)
        self.prompts = CoopMultiLlmAgentV2Prompts()
        self.agents = {"player": {"system_prompt": self.prompts.player_prompt},
                       "role_finder": {"system_prompt": self.prompts.role_finder_prompt},
                       "log_analyzer": {"system_prompt": self.prompts.log_analyzer_prompt},
                       "cooperator": {"system_prompt": self.prompts.cooperator_prompt},
                       "summarizer": {"system_prompt": self.prompts.summarizer_prompt}, }
        self.coop_agent_answer = ""

    def ask_llm(self, prompt: str, agents: list, so_answer_field_name: Union[str, None] = "result") -> str:
        if not agents:
            agents = self.base_agents_list()
        self.coop_agent_answer = ""
        answer, json_objects, errors = self.generate_answer(prompt, agents=agents)
        while (errors
               or (not json_objects and so_answer_field_name)
               or (json_objects and so_answer_field_name and not json_objects[0].get(so_answer_field_name))):
            prompt = {"prompt": self.prompts.get_regenerate_prompt(so_answer_field_name, errors)}
            answer, json_objects, errors = self.generate_answer(prompt, regenerate=True)

        json_object = json_objects[0]
        users_role = json_object.get("users_role")
        say_to_all = json_object.get("say_to_all")
        if self.coop_agent_answer:
            say_to_all = self.coop_agent_answer

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

            if agent == "cooperator":
                pattern = r'"(.*?)"'
                match = re.search(pattern, answer, re.DOTALL)

                if match:
                    message = match.group(1)
                    print("===" * 30)
                    print("Cooperator SAY_TO_ALL:")
                    print(message)
                    print("===" * 30)
                    self.coop_agent_answer = message

        task_context.pop(prompt_pos)
        self.chat_context.extend(task_context)

        json_objects, errors = self.extract_json_objects(row_text=answer)
        return answer, json_objects, errors