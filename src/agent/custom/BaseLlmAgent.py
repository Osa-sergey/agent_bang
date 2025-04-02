from typing import Any

from src.agent.Agent import Agent
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player


class BaseLlmAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        self.sleep_delay = 0
        super().__init__(agent_name, config, player, game, shared_memory)


    def __get_player_current_state(self) -> str:
        state = self.player.get_state_log()
        text_state = ""
        return text_state

    def choice_card_for_play(self) -> str:
        pass

    def get_opponent(self, card: Card) -> str:
        pass

    def get_action_type(self, card: Card) -> str:
        pass

    def get_card_for_steal(self, card: Card) -> str:
        pass

    def get_indians_response(self) -> str:
        pass

    def get_bang_response(self) -> str:
        pass

    def get_gatling_response(self) -> str:
        pass

    def get_card_for_discard(self, num_cards: int) -> str:
        pass

    def react_to_discard_error(self, errors: str):
        pass

