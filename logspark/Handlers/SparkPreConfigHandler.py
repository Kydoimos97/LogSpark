import logging
import sys

from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode
from ..Types.Protocol import SupportsWrite


class SparkPreConfigHandler(logging.StreamHandler[SupportsWrite]):
    def __init__(self, stream: SupportsWrite = sys.stdout) -> None:
        stream = stream or sys.stdout
        if is_silenced_mode():
            stream = get_devnull()

        super().__init__(stream=stream)
        fmt = logging.Formatter(
            fmt="(PreConfig) %(asctime)-8s %(levelname)-8s - %(filename)s:%(lineno)d -> %(message)s",
            datefmt="%H:%M:%S",
        )
        self.setFormatter(fmt)
