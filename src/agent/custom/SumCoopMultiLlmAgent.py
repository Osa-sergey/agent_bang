import json
from typing import Any, Union, Dict, Sequence
import re

from openai import OpenAI

from src.agent.Agent import Agent
from src.agent.custom.CoopMultiLlmAgentV2 import CoopMultiLlmAgentV2
from src.agent.custom.SumCoopMultiLlmAgentPrompt import SumCoopMultiLlmAgentPrompts
from src.emulator.Emulator import LogEventType
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player
from src.game.Utils import GameEncoder


class SumCoopMultiLlmAgent(CoopMultiLlmAgentV2):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):

        super().__init__(agent_name, config, player, game, shared_memory)
        self.prompts = SumCoopMultiLlmAgentPrompts()
        self.agents = {"player": {"system_prompt": self.prompts.player_prompt},
                       "role_finder": {"system_prompt": self.prompts.role_finder_prompt},
                       "log_analyzer": {"system_prompt": self.prompts.log_analyzer_prompt},
                       "cooperator": {"system_prompt": self.prompts.cooperator_prompt},
                       "summarizer": {"system_prompt": self.prompts.summarizer_prompt}, }
        self.summary_gen_conf =  self.agent_config["summary_gen_conf"]

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
        if not regenerate:
            system_prompt = [{"role": "system", "content": self.prompts.task_summarize_prompt}]
            all_context = system_prompt + self.chat_context + task_context

            summarization = self.llm_api_call(all_context, self.summary_gen_conf)
        
            print("===" * 30)
            print(f"Summarization")
            print("Raw answer: ")
            print(summarization)
            self.chat_context.append({"role": "assistant", "content": summarization})
        else:
            self.chat_context.extend(task_context)

        json_objects, errors = self.extract_json_objects(row_text=answer)
        return answer, json_objects, errors

