from typing import Any, Callable


class LoggedList(list):
    def __init__(self,
                 log_func: Callable[[dict[str, Any], str], None],
                 file_name: str,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__log_func = log_func
        self.__file_name = file_name

    def append(self, data: dict[str, Any]) -> None:
        super().append(data)
        self.__log_func(data, self.__file_name)
