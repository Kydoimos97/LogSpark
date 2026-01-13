import logging
import sys

from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode


def pre_config_handler() -> logging.Handler:
    """
    Create pre-configuration handler for early logging before SparkLogger setup.
    
    Returns a StreamHandler that outputs to stdout (or devnull in silenced mode)
    with a formatted message including the "No-Config" prefix to indicate
    the logger hasn't been properly configured yet.
    
    Returns:
        logging.Handler: Configured StreamHandler for pre-configuration logging.
    """
    stream = sys.stdout
    if is_silenced_mode():
        stream = get_devnull()

    # stdlib StreamHandler
    handler = logging.StreamHandler(stream)
    fmt = logging.Formatter(
        fmt="(PreConfig) %(asctime)-8s %(levelname)-8s - %(filename)s:%(lineno)d -> %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)

    return handler
