import random
from typing import Any

from src.agent.Agent import Agent
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player


class DummyAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        super().__init__(agent_name, config, player, game, shared_memory)

    def choice_card_for_play(self) -> str:
        if self.player.get_state_log()["cur_hp"] >= len(self.player_hand):
            return "end"
        else:
            player_card_ids = [card.card_id.value for card in self.player_hand]
            for i in range(2):
                card_id = random.choice(player_card_ids)
                if card_id == "miss":
                    continue
                if card_id == "bang":
                    if self.player.can_use_weapon:
                        return card_id
                else:
                    return card_id

            return "end"

    def get_opponent(self, card: Card) -> str:
        all_players = self.game.get_player_names()
        my_name = self.player.name
        my_index = all_players.index(my_name)
        if my_index == len(all_players) - 1:
            options = [all_players[my_index - 1], all_players[0]]
        elif my_index == 0:
            options = [all_players[-1], all_players[1]]
        else:
            options = [all_players[my_index - 1], all_players[my_index + 1]]
        return random.choice(options)

    def get_action_type(self, card: Card, options: dict) -> str:
        return "from_hand"

    def get_card_for_steal(self, card: Card, options: dict) -> str:
        return input(f"Enter the name of the card: ").strip().lower()

    def get_indians_response(self) -> str:
        return "bang"

    def get_bang_response(self) -> str:
        return "miss"

    def get_gatling_response(self) -> str:
        return "miss"

    def get_card_for_discard(self, num_cards: int) -> str:
        discarded = []
        for i in range(num_cards):
            discarded.append(self.player_hand[i].card_id.value)
        return " ".join(discarded)

    def react_to_discard_error(self, errors: str):
        pass