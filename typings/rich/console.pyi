from typing import (
    IO,
    Any,
    NamedTuple,
    Protocol,
    TypeAlias,
    Union,
    runtime_checkable,
)

class ConsoleDimensions(NamedTuple):
    width: int
    height: int

class ConsoleOptions: ...
class RenderResult: ...

@runtime_checkable
class ConsoleRenderable(Protocol):
    def __rich_console__(
        self,
        console: "Console",
        options: ConsoleOptions,
    ) -> RenderResult: ...

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

    def __init__(
        self,
        *,
        file: IO[str] | None = ...,
        width: int | None = ...,
        height: int | None = ...,
        tab_size: int = ...,
        no_color: bool = ...,
        **kwargs: Any,
    ) -> None: ...
    @property
    def size(self) -> ConsoleDimensions: ...
    def get_datetime(self) -> Any: ...
