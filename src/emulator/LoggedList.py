import json
from enum import Enum
from typing import Any, Callable
import dearpygui.dearpygui as dpg

from src.game.Config import Config
from src.game.Utils import GameEncoder


class SavePath(Enum):
    SHARED_MEMORY = "shared_memory_log.json"
    LOCAL_MEMORY = "local_log.json"

class LoggedList(list):
    def __init__(self,
                 log_func: Callable[[dict[str, Any], str], None],
                 file_name: SavePath,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__log_func = log_func
        self.__file_name = file_name

    def append(self, data: dict[str, Any]) -> None:
        super().append(data)
        self.__log_func(data, self.__file_name.value)

        if Config().config.gui:
            data = json.dumps(data, indent=2, ensure_ascii=False, cls=GameEncoder)
            match self.__file_name:
                case SavePath.SHARED_MEMORY:
                    dpg.add_text(data, parent="game_log")
                case SavePath.LOCAL_MEMORY:
                    dpg.add_text(data, parent="agent_log")
