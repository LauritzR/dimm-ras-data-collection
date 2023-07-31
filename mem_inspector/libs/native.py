from typing import Callable, Dict, List

from libs.data_processors import AbsDataProcessor
from libs.logger import pmon_logger as logger


class NativeCallMap:
    """
    Class: NativeCallMap
    Description: This is a reflection map for calling native Python
    defs / methods based on their name string
    """

    map: Dict[str, Callable[[AbsDataProcessor, List[str]], None]] = {}

    @staticmethod
    async def cmd(name: str, command: List[str], out: AbsDataProcessor) -> None:
        logger.debug(f"Calling function {name} {command=}")
        if (
            command
            and command[0] in NativeCallMap.map
            and callable(NativeCallMap.map[command[0]])
        ):
            # since command[0] is a name of executable/native procedure
            # we need to deliver an optional arguments only
            # this is analogy to sys.argv[0]
            # i.e
            #   [commands.pmoncntr]
            #       cmd = pmoncntr "0000:24:0A.0" 1
            await NativeCallMap.map[command[0]](out, command[1:])  # type: ignore
        else:
            logger.error(f"Calling function {name}:{command} failed")

    @staticmethod
    def register(
        name: str, func: Callable[[AbsDataProcessor, List[str]], None]
    ) -> None:
        NativeCallMap.map[name] = func
