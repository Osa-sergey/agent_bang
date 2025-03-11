import random
from collections import deque
import datetime
from enum import Enum
from json import JSONEncoder

from Card import Card
from Role import Role

class GameEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return {"name": obj.name, "value": obj.value}
        if isinstance(obj, deque):
            return list(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Card):
            return {"card_id": obj.card_id.value, "card_type": obj.card_type.value}
        return super().default(obj)

def check_player_roles(config):
    if len(config.players) != config.players_number:
        raise Exception('The players_number field is not equal to the number of players')
    if config.players_number < 4 or  config.players_number > 7:
        raise Exception('The number of players does not correspond to the allowed number of players in the rules')

    roles = {}
    match config.players_number:
        case 4:
            roles = {Role.SHERIFF: 1, Role.RENEGADE: 1, Role.BANDIT: 2}
        case 5:
            roles = {Role.SHERIFF: 1, Role.SHERIFF_ASSISTANT: 1, Role.RENEGADE: 1, Role.BANDIT: 2}
        case 6:
            roles = {Role.SHERIFF: 1, Role.SHERIFF_ASSISTANT: 1, Role.RENEGADE: 1, Role.BANDIT: 3}
        case 7:
            roles = {Role.SHERIFF: 1, Role.SHERIFF_ASSISTANT: 2, Role.RENEGADE: 1, Role.BANDIT: 3}

    for player in config.players:
        role = Role(player.role)
        roles[role] = roles[role] - 1

    for role_n in roles.values():
        if role_n != 0:
            raise Exception("The set of roles does not correspond to the rules and the number of players")

def shuffle(items):
    random.shuffle(items)

