import sys

from ...Types.Protocol import SupportsWrite
from ..State import is_silenced_mode
from .get_devnull import get_devnull


def resolve_stream(stream: SupportsWrite | None) -> SupportsWrite:
    resolved: SupportsWrite = stream if stream is not None else sys.stdout
    if is_silenced_mode():
        resolved = get_devnull()
    return resolved
