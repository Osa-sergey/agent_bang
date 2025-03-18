import json
import os.path
import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from src.game.Card import Card
from src.emulator.LoggedList import LoggedList, SavePath
from src.game.Game import Game
from src.game.Player import Player
from src.game.Utils import GameEncoder


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
        self.__local_memory = LoggedList(self._save_local_memory, SavePath.LOCAL_MEMORY)
        self.player = player # only for read purpose
        self.game = game # only for read purpose
        self.__shared_memory = shared_memory

    @property
    def player_hand(self):
        return self.player.get_state_log()["hand"]

    @property
    def local_memory(self):
        return self.__local_memory

    @property
    def shared_memory(self):
        return self.__shared_memory

    def _save_local_memory(self, data: dict[str, Any], file_name: str):
        data["dttm"] = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
        log_file = os.path.join(self.__agent_log_path, file_name)
        with open(log_file, "a", encoding="utf-8") as f:
            json.dump(data, f, indent=4, cls=GameEncoder)

    def __get_player_current_state(self) -> str:
        state = self.player.get_state_log()
        text_state = ""
        return text_state

    @abstractmethod
    def choice_card_for_play(self) -> str:
        pass

    @abstractmethod
    def get_opponent(self, card: Card) -> str:
        pass

    @abstractmethod
    def get_action_type(self, card: Card) -> str:
        pass

    @abstractmethod
    def get_card_for_steal(self, card: Card) -> str:
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
