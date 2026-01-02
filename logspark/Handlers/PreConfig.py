import logging
import sys

from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode


def pre_config_handler() -> logging.Handler:
    """
    Create pre-configuration handler
    """
    stream = sys.stderr
    if is_silenced_mode():
        stream = get_devnull()

    # stdlib StreamHandler
    handler = logging.StreamHandler(stream)
    fmt = logging.Formatter(
        fmt="%(asctime)-8s - %(filename)s:%(lineno)d - %(levelname)-8s -> %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)

    return handler
