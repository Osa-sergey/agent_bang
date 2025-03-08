import typing
from collections import deque

from omegaconf import OmegaConf

from Card import Card, CardID
from Config import Config
from Utils import shuffle


class Deck:
    def __init__(self):
        self.__deck = self.__init_cards()
        self.__discard_pile = deque()


    def get_state_log(self):
        return {"deck": self.__deck, "discard_pile": self.__discard_pile}


    @staticmethod
    def __init_cards() -> deque:
        cards = []
        cards_config = OmegaConf.to_object(Config().config.cards)
        for card, quantity in cards_config.items():
            cards.extend([Card(CardID(card))] * quantity)

        cards_deque = deque(cards)
        shuffle(cards_deque)
        return cards_deque


    def discard(self, card: Card):
        self.__discard_pile.append(card)


    def draw(self) -> typing.Union[Card, None]:
        if not self.__deck:
            self.__deck = self.__discard_pile
            self.__discard_pile = deque()
            shuffle(self.__deck)
        if self.__deck:
            return self.__deck.pop()
        return None