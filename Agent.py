import json
import os.path
import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from Card import Card
from Memory import MemoryList
from Player import Player
from Utils import GameEncoder


class AgentType(Enum):
    USER_AGENT = "user_agent"


class Agent(ABC):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 shared_memory: MemoryList):
        self.name = agent_name
        self.__agent_config = config["agents"][self.name]
        self.__agent_log_path = os.path.join(config["save_path"], "agents", self.name)
        os.makedirs(self.__agent_log_path)
        self.__local_memory = MemoryList(self._save_local_memory, "local_memory.jsonl")
        self.__player = player
        self.__shared_memory = shared_memory

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
        state = self.__player.get_state_log()
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


class UserAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 shared_memory: MemoryList):
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