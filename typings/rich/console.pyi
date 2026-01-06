from datetime import datetime
from enum import IntEnum
from typing import (
    IO,
    Iterable,
    NamedTuple,
    Protocol,
    TypeAlias,
    Union,
    runtime_checkable,
    )

from .segment import Segment


class ConsoleDimensions(NamedTuple):
    width: int
    height: int

class ColorSystem(IntEnum): ...

class ConsoleOptions: ...

RenderResult = Iterable[Union[RenderableType, Segment]]

@runtime_checkable
class ConsoleRenderable(Protocol):
    def __rich_console__(
        self,
        console: "Console",
        options: ConsoleOptions,
    ) -> Iterable[ConsoleRenderable | RichCast | str | Segment]: ...

@runtime_checkable
class RichCast(Protocol):
    def __rich__(self) -> Union["ConsoleRenderable", "RichCast", str]: ...

RenderableType: TypeAlias = Union[
    ConsoleRenderable,
    RichCast,
    str,
]

class Console:
    file: IO[str] | None
    _color_system: ColorSystem | None

    def __init__(
        self,
        *,
        file: IO[str] | None = ...,
        width: int | None = ...,
        height: int | None = ...,
        tab_size: int = ...,
        no_color: bool = ...,
        **kwargs: object,
    ) -> None: ...

    @property
    def size(self) -> ConsoleDimensions: ...

    @property
    def width(self) -> int:
        ...

    def get_datetime(self) -> datetime: ...

    def _detect_color_system(self) -> ColorSystem | None: ...