import sys

from ...Types.Protocol import SupportsWrite
from ..State import is_silenced_mode
from .get_devnull import get_devnull


def resolve_stream(stream: SupportsWrite | None) -> SupportsWrite:
    stream = stream or sys.stdout
    if is_silenced_mode():
        stream = get_devnull()
    return stream
