import json
import random
from enum import Enum
from typing import Union

from src.game.Card import Card, CardID, CardType
from src.game.Deck import Deck
from src.game.Role import Role
from src.game.Utils import GameEncoder


class PlayerActionResponse(Enum):
    BANG = "bang"
    MISS = "miss"
    PASS = "pass"


class Player:
    def __init__(self, deck: Deck, hand: list[Card], player_config):
        self.__deck = deck
        self.name = player_config.name
        self.__role = Role(player_config.role)
        self.__hand = hand

        self.__max_hp = player_config.max_hp
        self.__cur_hp = self.__max_hp if self.__role != Role.SHERIFF else self.__max_hp + 1
        self.__weapon = "default"
        self.__weapon_range = 1
        self.can_use_weapon = True
        self.__effects = []

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return False
        return self.name == other.name and self.__role == other.__role

    def __str__(self):
        hand = json.dumps(self.__hand, cls=GameEncoder, indent=4)
        effects = json.dumps(self.__effects, cls=GameEncoder, indent=4)
        return (f"""Person name='{self.name}'
         {'===' * 20}
         role='{self.__role}',
         weapon='{self.__weapon}',
         weapon_range='{self.__weapon_range}',
         cur_hp='{self.__cur_hp}',
         max_hp='{self.__max_hp}',
         {'===' * 20}
         Hand:
         {hand}
         {'===' * 20}
         Effects:
         {'===' * 20}
         {effects}

        """)

    def get_dist_modifiers(self):
        return {
            "for_shoot": 1 if Card(CardID.SCOPE) in self.__effects else 0,
            "for_save": 1 if Card(CardID.MUSTANG) in self.__effects else 0,
                }

    def has_card(self, card: Card) -> bool:
        return card in self.__hand

    def add_card_to_hand(self, card):
        self.__hand.append(card)

    def get_random_card_from_hand(self) -> Card:
        return self.__hand.pop(random.randrange(len(self.__hand)))

    def get_card_from_game(self, card: Card) -> Card:
        match card.card_type:
            case CardType.WEAPON:
                if self.__weapon != card:
                    raise Exception(f"The player does not have such a weapon {card} in the game")
                self.__weapon = "default"
                self.__weapon_range = 1
            case CardType.EFFECT:
                if card not in self.__effects:
                    raise Exception(f"The player does not have such a effect {card} in the game")
                self.__effects.remove(card)
            case CardType.ACTION:
                raise Exception(f"You can't steal card like that {card}")
        return card

    def play_effect_card(self, new_effect: Card):
        if new_effect in self.__effects:
            self.__deck.discard(new_effect)
        else:
            self.__effects.append(new_effect)
        self.__hand.remove(new_effect)

    def play_weapon_card(self, new_weapon: Card):
        if self.__weapon != "default":
            self.__deck.discard(self.__weapon)
        self.__weapon = new_weapon
        self.__weapon_range = new_weapon.get_range()
        self.__hand.remove(new_weapon)

    def get_health(self):
        return self.__cur_hp

    def decrease_health(self):
        self.__cur_hp -= 1

    def increase_health(self) -> bool:
        if self.__cur_hp + 1 <= self.__max_hp:
            self.__cur_hp += 1
            return True
        return False

    def death(self):
        for card in self.__hand:
            self.__deck.discard(card)
        self.__hand = []
        for card in self.__effects:
            self.__deck.discard(card)
        self.__effects = []
        if isinstance(self.__weapon, Card):
            self.__deck.discard(self.__weapon)
        self.__weapon = "default"

    def discard_cards_from_hand(self, discarded_cards: Union[list[Card], Card]) -> list[Card]:
        if not isinstance(discarded_cards, list):
            discarded_cards = [discarded_cards]
        errors = []
        for card in discarded_cards:
            try:
                self.__hand.remove(card)
                self.__deck.discard(card)
            except ValueError:
                errors.append(card)
        return errors

    def need_to_discard(self) -> int:
        num_discard_cards = len(self.__hand) - self.__cur_hp
        if num_discard_cards > 0:
            return num_discard_cards
        else:
            return 0

    def draw_cards(self, num_cards: int):
        for i in range(num_cards):
            self.__hand.append(self.__deck.draw())

    def start_of_turn(self):
        self.draw_cards(2)

    def end_of_turn(self):
        self.can_use_weapon = True

    def get_game_state(self):
        return {
            "name": self.name,
            "role": Role.SHERIFF.value if self.__role == Role.SHERIFF else "unknown",
            "max_hp": self.__max_hp,
            "cur_hp": self.__cur_hp,
            "weapon": self.__weapon,
            "weapon_range": self.__weapon_range,
            "hand_size": len(self.__hand),
            "effects": self.__effects
        }

    def get_state_log(self):
        return {
            "name": self.name,
            "role": self.__role.value,
            "max_hp": self.__max_hp,
            "cur_hp": self.__cur_hp,
            "weapon": self.__weapon,
            "weapon_range": self.__weapon_range,
            "hand": self.__hand,
            "effects": self.__effects
        }