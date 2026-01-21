from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich._log_render import FormatTimeCallable

from .emit_warning import emit_warning

_default_timeformat = "%H:%M:%S"


def emit_invalid_timeformat_warning() -> None:
    class InvalidTimeFormatWarning(UserWarning):
        """Console does not support requested timeformat"""

        pass

    msg = (
        "\nWARNING: Requested timeformat is invalid\n"
        "  | falling back to default timeformat: %H:%M:%S"
    )

    emit_warning(
        message=msg,
        category=InvalidTimeFormatWarning,
        stacklevel=4,
    )


def validate_rich_timeformat(
    time_format: "str | FormatTimeCallable | None",
) -> "str | FormatTimeCallable":
    if time_format is None:
        return _default_timeformat
    if isinstance(time_format, str):
        try:
            datetime.fromisoformat(time_format)
            return time_format
        except Exception:
            emit_invalid_timeformat_warning()
            return _default_timeformat
    return time_format


def validate_stdlib_timeformat(time_format: str | object | None) -> str:
    if time_format is None:
        return _default_timeformat
    if isinstance(time_format, str):
        try:
            datetime.fromisoformat(time_format)
            return time_format
        except Exception:
            emit_invalid_timeformat_warning()
            return _default_timeformat
    emit_invalid_timeformat_warning()
    return _default_timeformat
