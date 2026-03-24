import os

from ...Types.Protocol import SupportsWrite


def get_devnull() -> SupportsWrite:
    return open(  # noqa: SIM115
        os.devnull,
        mode="w",
        encoding="utf-8",
        errors="replace",
    )
