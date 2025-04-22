from typing import Any

from src.agent.custom.BaseMultiLlmAgent import BaseMultiLlmAgent
from src.agent.custom.CoopMultiLlmAgentPrompts import CoopMultiLlmAgentPrompts
from src.emulator.LoggedList import LoggedList
from src.game.Game import Game
from src.game.Player import Player


class CoopMultiLlmAgent(BaseMultiLlmAgent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):

        super().__init__(agent_name, config, player, game, shared_memory)
        self.prompts = CoopMultiLlmAgentPrompts()
        self.agents = {"player": {"system_prompt": self.prompts.player_prompt},
                       "role_finder": {"system_prompt": self.prompts.role_finder_prompt},
                       "log_analyzer": {"system_prompt": self.prompts.log_analyzer_prompt},
                       "cooperator": {"system_prompt": self.prompts.cooperator_prompt},
                       "summarizer": {"system_prompt": self.prompts.summarizer_prompt}, }