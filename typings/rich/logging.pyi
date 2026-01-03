from logging import Handler, LogRecord
from .console import Console

class RichHandler(Handler):
    console: Console
    enable_link_path: bool

    def __init__(
        self,
        level: int | str = ...,
        console: Console | None = ...,
        *,
        show_time: bool = ...,
        show_level: bool = ...,
        show_path: bool = ...,
        markup: bool = ...,
        rich_tracebacks: bool = ...,
        **kwargs: object,
    ) -> None: ...

    def get_level_text(self, record: LogRecord) -> str: ...
