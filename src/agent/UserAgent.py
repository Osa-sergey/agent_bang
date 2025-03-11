from typing import Any

from src.game.Card import Card
from src.emulator.LoggedList import LoggedList
from src.game.Player import Player
from src.agent.Agent import Agent


class UserAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 shared_memory: LoggedList):
        super().__init__(agent_name, config, player, shared_memory)

    def choice_card_for_play(self) -> str:
        return input(f"Enter the name of a card to play or end to end a turn: ").strip()

    def get_opponent(self, card: Card) -> str:
        return input(f"Enter your opponent's name: ").strip().lower()

    def get_action_type(self, card: Card) -> str:
        return input(f"Enter where the card should be from (from_hand, from_play): ").strip().lower()

    def get_card_for_steal(self, card: Card) -> str:
        return input(f"Enter the name of the card: ").strip().lower()

    def get_indians_response(self) -> str:
        return input(f"Choose an action in response to the Indians card (bang, pass): ").strip().lower()

    def get_bang_response(self) -> str:
        return input(f"Choose an action in response to the bang card (miss, pass): ").strip().lower()

    def get_gatling_response(self) -> str:
        return input(f"Choose an action in response to the gatling card (miss, pass): ").strip().lower()

    def get_card_for_discard(self, num_cards: int) -> str:
        return input(f"Enter {num_cards} of the card names, separated by spaces: ").strip()

    def react_to_discard_error(self, errors: str):
        pass