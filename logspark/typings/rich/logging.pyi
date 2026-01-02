from logging import Handler, LogRecord
from typing import Any

class RichHandler(Handler):
    console: Any
    enable_link_path: bool

    def get_level_text(self, record: LogRecord) -> str: ...
