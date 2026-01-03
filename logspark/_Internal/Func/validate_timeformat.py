import warnings
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich._log_render import FormatTimeCallable

_default_timeformat = "[%H:%M:%S]"


def emit_invalid_timeformat_warning() -> None:
    class InvalidTimeFormatWarning(UserWarning):
        """Console does not support requested timeformat"""

        pass

    warnings.warn(
        message="Requested timeformat is invalid falling back to default timeformat: [%H:%M:%S]",
        category=InvalidTimeFormatWarning,
        stacklevel=2,
        source="LogSpark",
    )


def validate_rich_timeformat(time_format: "str | FormatTimeCallable") -> "str | FormatTimeCallable":
    if isinstance(time_format, str):
        try:
            datetime.now().strftime(time_format)
            return time_format
        except Exception:
            emit_invalid_timeformat_warning()
            return _default_timeformat
    return time_format


def validate_stdlib_timeformat(time_format: str | object) -> str:
    if isinstance(time_format, str):
        try:
            datetime.now().strftime(time_format)
            return time_format
        except Exception:
            emit_invalid_timeformat_warning()
            return _default_timeformat
    return _default_timeformat
