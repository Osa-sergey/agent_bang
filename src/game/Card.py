from enum import Enum

class CardID(Enum):
    BANG = "bang"
    BEER = "beer"
    MISS = "miss"
    MUSTANG = "mustang"
    SCOPE = "scope"
    HOTTIE = "hottie"
    SALOON = "saloon"
    GATLING = "gatling"
    PANIC = "panic"
    INDIANS = "indians"
    FARGO = "fargo"
    STAGECOACH = "stagecoach"
    VOLKANIC = "volkanic"
    SCOFIELD = "scofield"
    REMINGTON = "remington"
    CARBINE = "carbine"
    WINCHESTER = "winchester"


class CardType(Enum):
    ACTION = 0
    EFFECT = 1
    WEAPON = 2


class CardActionRequest(Enum):
      RESPONSE_TO_BANG = "response to bang"
      RESPONSE_TO_GATLING = "response to gatling"
      RESPONSE_TO_INDIANS = "response to indians"


class Card:
    def __init__(self, card_id: CardID):
        self.card_id = card_id
        self.card_type = self.__get_card_type()

    def __repr__(self):
        return str({"card_id": self.card_id.name,
                "card_type": self.card_type.name})

    def __hash__(self):
        return hash((self.card_id, self.card_type))

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.card_id.value == other.card_id.value and self.card_type.value == other.card_type.value
        return False

    def __str__(self):
        return f"Card name: {self.card_id.value} \nCard type: {self.card_type.name}"

    def __get_card_type(self) -> CardType:
        match self.card_id:
            case CardID.WINCHESTER | CardID.CARBINE | CardID.REMINGTON | CardID.SCOFIELD | CardID.VOLKANIC:
                return CardType.WEAPON
            case CardID.MUSTANG | CardID.SCOPE:
                return CardType.EFFECT
            case _:
                return CardType.ACTION

    def get_range(self):
        match self.card_id:
            case CardID.VOLKANIC:
                return 1
            case CardID.SCOFIELD:
                return 2
            case CardID.REMINGTON:
                return 3
            case CardID.CARBINE:
                return 4
            case CardID.WINCHESTER:
                return 5
            case _:
                raise Exception("Support only CardType.WEAPON")


