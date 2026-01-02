import os
from io import TextIOWrapper


def get_devnull() -> TextIOWrapper:
    devnull = open(
        os.devnull,
        mode="w",
        encoding="utf-8",
        errors="replace",
    )
    return devnull
