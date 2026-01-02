import logging
import sys
import threading
from types import FrameType

from ..State import is_fast_mode

_CACHED_SL: int | None = None
_CALIBRATION_LOCK = threading.Lock()
_INTERNAL_PREFIX = "logspark"

# Limits
_RUNTIME_MAX_DEPTH = 25  # Slightly more breathing room for typical wrappers
_CALIBRATION_DEPTH = 500  # Deep enough for Hypothesis + Pytest + Middleware stacks


def _is_internal(frame: FrameType) -> bool:
    """
    Checks if the frame belongs to the LogSpark library.
    Using .startswith ensures we catch submodules like logspark.handlers.
    """
    # We use .get() because some frames (like those from exec())
    # might not have __name__ in globals.
    module = str(frame.f_globals.get("__name__", ""))
    return module.startswith(_INTERNAL_PREFIX)


def _calibrate_fast_stacklevel() -> int:
    """
    A deep, one-time probe.
    500 frames is more than enough for even the most complex Hypothesis tests.
    """
    found_level = 3

    class _ProbeHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            nonlocal found_level
            f: FrameType | None = sys._getframe(0)
            # Exhaustive search for the one-off calibration
            for level in range(1, _CALIBRATION_DEPTH):
                if f is None:
                    break
                if not _is_internal(f):
                    found_level = level
                    return
                f = f.f_back

    # Using a unique name to avoid collision with user loggers
    logger = logging.getLogger("_logspark_internal_probe")
    logger.propagate = False
    handler = _ProbeHandler()
    logger.addHandler(handler)

    try:
        logger.debug("probe")
    finally:
        logger.removeHandler(handler)
    return found_level


def resolve_stacklevel(user_stacklevel: int = 1) -> int:
    """
    Returns the stacklevel for logging.
    Falls back to a deep-calibrated value if dynamic walking gets lost.
    """
    if not is_fast_mode():
        try:
            frame: FrameType | None = sys._getframe(2)
            for level in range(1, _RUNTIME_MAX_DEPTH):
                if frame is None:
                    break
                if not _is_internal(frame):
                    return level + user_stacklevel
                frame = frame.f_back
        except (ValueError, AttributeError):
            pass

    # Global access to the one-time measurement
    global _CACHED_SL
    if _CACHED_SL is None:
        with _CALIBRATION_LOCK:
            if _CACHED_SL is None:
                _CACHED_SL = _calibrate_fast_stacklevel()

    return _CACHED_SL + user_stacklevel - 2
