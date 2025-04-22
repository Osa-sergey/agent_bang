import json
import os.path
import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from openai import OpenAI

from src.game.Card import Card
from src.emulator.LoggedList import LoggedList, SavePath
from src.game.Game import Game
from src.game.Player import Player
from src.game.Utils import GameEncoder

class AgentType(Enum):
    DEEPSEEK = 0


def init_agent(agent_type: AgentType = AgentType.DEEPSEEK):
    client = None
    match agent_type:
        case AgentType.DEEPSEEK:
            deepseek_api_key = os.getenv('DEEPSEEK_KEY', "empty")
            if deepseek_api_key == "empty":
                raise Exception("Add api key to env variable DEEPSEEK_KEY")
            client = OpenAI(
                api_key= deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
    return client


class Agent(ABC):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        self.name = agent_name
        self.agent_config = config["agents"][self.name]
        self.__agent_log_path = os.path.join(config["save_path"], "agents", self.name)
        os.makedirs(self.__agent_log_path)
        self.__local_log = LoggedList(self._save_local_memory, SavePath.LOCAL_MEMORY)
        self.__shared_memory = shared_memory
        self.__last_shared_memory_index = len(shared_memory)
        self.player = player # only for read purpose
        self.game = game # only for read purpose

    @property
    def player_hand(self):
        return self.player.get_state_log()["hand"]

    @property
    def local_log(self):
        return self.__local_log

    @property
    def shared_memory(self):
        return self.__shared_memory

    def __get_player_current_state(self) -> str:
        state = self.player.get_state_log()
        text_state = json.dumps(state, cls=GameEncoder)
        return text_state

    def __get_last_memories(self) -> str:
        last_memories = json.dumps(self.shared_memory[self.__last_shared_memory_index: ], cls=GameEncoder)
        self.__last_shared_memory_index = len(self.shared_memory)
        return last_memories

    def get_game_state(self) -> dict[str, str]:
        return {
            "cur_state": self.__get_player_current_state(),
            "last_memories": self.__get_last_memories(),
        }

    def _save_local_memory(self, data: dict[str, Any], file_name: str):
        data["dttm"] = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
        log_file = os.path.join(self.__agent_log_path, file_name)
        with open(log_file, "a", encoding="utf-8") as f:
            json.dump(data, f, cls=GameEncoder)
            f.write('\n')

    @abstractmethod
    def choice_card_for_play(self) -> str:
        pass

    @abstractmethod
    def get_opponent(self, card: Card) -> str:
        pass

    @abstractmethod
    def get_action_type(self, card: Card, options: dict) -> str:
        pass

    @abstractmethod
    def get_card_for_steal(self, card: Card, options: dict) -> str:
        pass

    @abstractmethod
    def get_indians_response(self) -> str:
        pass

    @abstractmethod
    def get_bang_response(self) -> str:
        pass

    @abstractmethod
    def get_gatling_response(self) -> str:
        pass

    @abstractmethod
    def get_card_for_discard(self, num_cards: int) -> str:
        pass

    @abstractmethod
    def react_to_discard_error(self, errors: str):
        pass
