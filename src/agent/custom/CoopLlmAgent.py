from typing import Any

from src.agent.custom.CoopLlmAgentPrompts import CoopLlmAgentPrompts
from src.agent.custom.SpeakingLlmAgent import SpeakingLlmAgent
from src.emulator.LoggedList import LoggedList
from src.game.Game import Game
from src.game.Player import Player


class CoopLlmAgent(SpeakingLlmAgent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        super().__init__(agent_name, config, player, game, shared_memory)
        self.prompts = CoopLlmAgentPrompts()
        self.system_prompt = self.prompts.system_prompt
        self.chat_context = [
            {"role": "system", "content": self.system_prompt}
        ]


