import pprint
from typing import Any, Union

from src.agent.custom.SpeakingLlmAgentPrompts import SpeakingLlmAgentPrompts
from src.agent.custom.BaseLlmAgent import BaseLlmAgent
from src.emulator.Emulator import LogEventType
from src.emulator.LoggedList import LoggedList
from src.game.Game import Game
from src.game.Player import Player


class SpeakingLlmAgent(BaseLlmAgent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        super().__init__(agent_name, config, player, game, shared_memory)
        self.prompts = SpeakingLlmAgentPrompts()
        self.system_prompt = self.prompts.system_prompt
        self.chat_context = [
            {"role": "system", "content": self.system_prompt}
        ]

    def ask_llm(self, prompt: dict[str, str], so_answer_field_name: Union[str, None] = "result") -> str:
        self.trim_chat_context()
        answer, json_objects, errors = self.generate_answer(prompt)
        while (errors
            or (not json_objects and so_answer_field_name)
            or (json_objects and so_answer_field_name and not json_objects[0].get(so_answer_field_name))):

            prompt = {"prompt": self.prompts.get_regenerate_prompt(so_answer_field_name, errors)}
            answer, json_objects, errors = self.generate_answer(prompt)

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

