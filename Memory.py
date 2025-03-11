from typing import Any, Callable


class MemoryList(list):
    def __init__(self,
                 process_func: Callable[[dict[str, Any], str], None],
                 file_name: str,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__process_func = process_func
        self.__file_name = file_name

    def append(self, data: dict[str, Any]) -> None:
        super().append(data)
        self.__process_func(data, self.__file_name)
