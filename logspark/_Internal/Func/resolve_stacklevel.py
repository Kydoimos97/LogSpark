import logging
import sys
import threading
from types import FrameType

from ..State import is_fast_mode

_CACHED_SL: int | None = None
_CALIBRATION_LOCK = threading.Lock()
_PREFIX_CACHE: dict[type, frozenset[str]] = {}
_CACHED_SL_BY_TYPE: dict[type, int] = {}

# Limits
_RUNTIME_MAX_DEPTH = 25  # Slightly more breathing room for typical wrappers
_CALIBRATION_DEPTH = 500  # Deep enough for Hypothesis + Pytest + Middleware stacks


def _get_mro_prefixes(cls: type | None) -> frozenset[str]:
    """
    Derive internal package prefixes from the MRO of a logger class.

    For the base SparkLogger (or None), returns frozenset({"logspark"}).
    For subclasses like WrenchLogger(SparkLogger), returns prefixes for
    all intermediate classes up to and including SparkLogger in logspark.

    Results are cached in _PREFIX_CACHE to avoid repeated MRO walks.
    """
    if cls is None:
        return frozenset({"logspark"})

    cached = _PREFIX_CACHE.get(cls)
    if cached is not None:
        return cached

    prefixes: set[str] = {"logspark"}
    for klass in cls.__mro__:
        mod = klass.__module__ or ""
        root = mod.split(".", 1)[0]
        if not root or root in {"logging", "builtins"}:
            continue
        prefixes.add(root)
        if root == "logspark" and klass.__name__ == "SparkLogger":
            break

    result = frozenset(prefixes)
    _PREFIX_CACHE[cls] = result
    return result


def _is_internal(frame: FrameType, prefixes: frozenset[str] | None = None) -> bool:
    """
    Checks if the frame belongs to internal library code.

    Internal frames are those whose module name (from frame.f_globals["__name__"])
    exactly matches one of the prefixes or starts with prefix + ".".

    If prefixes is None, defaults to frozenset({"logspark"}).
    """
    if prefixes is None:
        prefixes = frozenset({"logspark"})

    # We use .get() because some frames (like those from exec())
    # might not have __name__ in globals.
    module = str(frame.f_globals.get("__name__", ""))
    return any(module == p or module.startswith(f"{p}.") for p in prefixes)


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
            # Use only the base logspark prefixes for probe calibration
            base_prefixes = frozenset({"logspark"})
            for level in range(1, _CALIBRATION_DEPTH):
                if f is None:
                    break
                if not _is_internal(f, base_prefixes):
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


def resolve_stacklevel(user_stacklevel: int = 1, logger_cls: type | None = None) -> int:
    """
    Returns the stacklevel for logging.

    Resolves internal frames based on the MRO of logger_cls. If logger_cls is
    a subclass of SparkLogger (e.g., WrenchLogger), wrapper methods in that
    subclass are treated as internal and skipped, so the callsite points to
    the real caller.

    Falls back to a deep-calibrated value if dynamic walking gets lost or if
    fast mode is enabled and the logger class is not known.
    """
    global _CACHED_SL

    fast = is_fast_mode()

    # Fast mode: check per-type cache first — skip prefix computation on the hot path
    if fast and logger_cls is not None:
        cached = _CACHED_SL_BY_TYPE.get(logger_cls)
        if cached is not None:
            return cached + user_stacklevel

    prefixes = _get_mro_prefixes(logger_cls)

    # Dynamic walk: always in normal mode; in fast mode only for uncached subclass types
    if not fast or logger_cls is not None:
        try:
            frame: FrameType | None = sys._getframe(2)
            for level in range(1, _RUNTIME_MAX_DEPTH):
                if frame is None:
                    break
                if not _is_internal(frame, prefixes):
                    if fast and logger_cls is not None:
                        # Cache for future fast-mode calls from this subclass
                        _CACHED_SL_BY_TYPE[logger_cls] = level
                    return level + user_stacklevel
                frame = frame.f_back
        except (ValueError, AttributeError):
            pass

    # Probe-calibrated fallback (fast mode base case, or dynamic walk failed)
    if _CACHED_SL is None:
        with _CALIBRATION_LOCK:
            if _CACHED_SL is None:
                _CACHED_SL = _calibrate_fast_stacklevel()
    return _CACHED_SL + user_stacklevel - 2
