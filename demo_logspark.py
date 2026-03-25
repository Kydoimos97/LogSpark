"""
LogSpark capabilities demo.

Run:  uv run python demo_logspark.py
Deps: logspark installed; `rich` and `python-json-logger` optional but recommended.
"""

import io
import logging

from logspark import TempLogLevel, logger, spark_log_manager
from logspark.Handlers import SparkJsonHandler, SparkTerminalHandler
from logspark.Types.Options import PathResolutionSetting, TracebackOptions


def _section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. Pre-configure: logging before configure() is called
# ---------------------------------------------------------------------------
_section("1. Pre-configure fallback")

# The logger is not yet configured.  LogSpark emits a one-time warning and
# falls back to SparkPreConfigHandler so records are never silently dropped.
logger.info("Logged before configure() -- uses fallback handler")

# ---------------------------------------------------------------------------
# 2. Minimal configure() with all defaults
# ---------------------------------------------------------------------------
_section("2. Minimal configure() -- SparkTerminalHandler, INFO, COMPACT tracebacks")

logger.kill()
logger.configure()

logger.debug("DEBUG -- not shown (level is INFO)")
logger.info("INFO message")
logger.warning("WARNING message")
logger.error("ERROR message")
logger.critical("CRITICAL message")

# ---------------------------------------------------------------------------
# 3. Structured data via extra=
# ---------------------------------------------------------------------------
_section("3. Structured data via extra=")

logger.kill()
logger.configure()

logger.info(
    "Request completed",
    extra={
        "method": "GET",
        "path": "/api/users",
        "status": 200,
        "duration_ms": 42,
    },
)

# ---------------------------------------------------------------------------
# 4. Exception logging -- traceback policies
#
# Policy is applied by formatters that call process_spark_log_record:
#   SparkColorFormatter, SparkRichHandler, SparkJsonFormatter.
# SparkBaseFormatter passes through to stdlib (no policy applied).
# Rich is used here so policy rendering is clear at any terminal width.
# ---------------------------------------------------------------------------
try:
    from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler as _RH
    from logspark.Types.Options import SparkRichHandlerSettings as _RHS
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_COMPACT_SETTINGS = _RHS(min_message_width=25, max_path_width=20) if _RICH_AVAILABLE else None

_section("4a. TracebackOptions.COMPACT -- type + message + single frame location")

logger.kill()

if _RICH_AVAILABLE:
    logger.configure(
        handler=_RH(traceback_policy=TracebackOptions.COMPACT, settings=_COMPACT_SETTINGS)
    )
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division failed")
else:
    buf = io.StringIO()
    logger.configure(handler=SparkJsonHandler(stream=buf))
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division failed")
    print(buf.getvalue().strip())

_section("4b. TracebackOptions.FULL -- all frames")

logger.kill()
logger.configure(traceback_policy=TracebackOptions.FULL)
try:
    raise ValueError("something went wrong deeply")
except ValueError:
    logger.exception("Full traceback -- all frames")

_section("4c. TracebackOptions.HIDE -- exception type and message only")

logger.kill()

if _RICH_AVAILABLE:
    logger.configure(
        handler=_RH(traceback_policy=TracebackOptions.HIDE, settings=_COMPACT_SETTINGS)
    )
    try:
        raise RuntimeError("internal detail suppressed")
    except RuntimeError:
        logger.exception("No location shown")
else:
    buf = io.StringIO()
    logger.configure(handler=SparkJsonHandler(stream=buf))
    try:
        raise RuntimeError("internal detail suppressed")
    except RuntimeError:
        logger.exception("No location shown")
    print(buf.getvalue().strip())

# ---------------------------------------------------------------------------
# 5. Path resolution settings
#
# SparkTerminalHandler uses %(filename)s in its format string so the path
# column always shows just the filename regardless of setting.
# SparkRichHandler reads record.spark.filepath (set by PathNormalizationFilter)
# so the three modes produce visually distinct output.
# ---------------------------------------------------------------------------
_PATH_SETTINGS = _RHS(min_message_width=20, max_path_width=55) if _RICH_AVAILABLE else None

_section("5a. PathResolutionSetting.FILE -- filename only")

logger.kill()
if _RICH_AVAILABLE:
    logger.configure(
        path_resolution=PathResolutionSetting.FILE,
        handler=_RH(show_path=True, settings=_PATH_SETTINGS),
    )
else:
    logger.configure(path_resolution=PathResolutionSetting.FILE)
logger.info("Path column: filename only")

_section("5b. PathResolutionSetting.ABSOLUTE -- full absolute path")

logger.kill()
if _RICH_AVAILABLE:
    logger.configure(
        path_resolution=PathResolutionSetting.ABSOLUTE,
        handler=_RH(show_path=True, settings=_PATH_SETTINGS),
    )
else:
    logger.configure(path_resolution=PathResolutionSetting.ABSOLUTE)
logger.info("Path column: full absolute path")

_section("5c. PathResolutionSetting.RELATIVE -- relative to project root (default)")

logger.kill()
if _RICH_AVAILABLE:
    logger.configure(
        path_resolution=PathResolutionSetting.RELATIVE,
        handler=_RH(show_path=True, settings=_PATH_SETTINGS),
    )
else:
    logger.configure(path_resolution=PathResolutionSetting.RELATIVE)
logger.info("Path column: project-relative path")

# ---------------------------------------------------------------------------
# 6. SparkTerminalHandler -- explicit configuration
# ---------------------------------------------------------------------------
_section("6. SparkTerminalHandler: show_function=True, multiline=False")

logger.kill()
handler = SparkTerminalHandler(show_function=True, multiline=False)
logger.configure(handler=handler)

logger.info("Function name column visible")

try:
    raise KeyError("missing key")
except KeyError:
    logger.exception("Single-line exception output")

# ---------------------------------------------------------------------------
# 7. SparkJsonHandler -- structured JSON output
# ---------------------------------------------------------------------------
_section("7. SparkJsonHandler -- single-line JSON output")

logger.kill()

try:
    buf = io.StringIO()
    json_handler = SparkJsonHandler(stream=buf)
    logger.configure(handler=json_handler)
    logger.info("JSON event", extra={"user_id": 42, "action": "login"})

    try:
        raise TypeError("json exception demo")
    except TypeError:
        logger.exception("Exception via JSON handler")

    print(buf.getvalue().strip())

except Exception as exc:
    print(f"  SparkJsonHandler unavailable: {exc}")

# ---------------------------------------------------------------------------
# 8. SparkRichHandler -- explicit Rich output
# ---------------------------------------------------------------------------
_section("8. SparkRichHandler -- explicit Rich handler (requires `rich`)")

logger.kill()

try:
    from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
    from logspark.Types.Options import SparkRichHandlerSettings

    settings = SparkRichHandlerSettings(min_message_width=40, max_path_width=23, omit_repeated_times=False)
    rich_handler = SparkRichHandler(settings=settings)
    logger.configure(handler=rich_handler)

    logger.info("Rich handler active -- structured column layout")
    logger.warning("Warning via Rich", extra={"key": "value"})

    try:
        raise TypeError("rich traceback demo")
    except TypeError:
        logger.exception("Exception via Rich handler")

except ImportError:
    logger.kill()
    logger.configure()
    logger.info("  `rich` not installed; SparkRichHandler skipped")

# ---------------------------------------------------------------------------
# 9. TempLogLevel -- context manager
#
# TempLogLevel only changes the logger level, not the handler level.  To
# allow DEBUG records through, the handler must have level=NOTSET (default
# when constructed without an explicit level argument).  Pass an explicit
# handler so the logger alone controls the effective minimum.
#
# Note: avoid calling logger.debug() *before* entering the context in this
# demo.  After kill(), the logger is removed from loggerDict and
# manager._clear_cache() cannot reach it, so a DEBUG=False cache entry
# written before the context would not be cleared when TempLogLevel runs.
# In production (no kill()), cache invalidation works correctly.
# ---------------------------------------------------------------------------
_section("9. TempLogLevel as a context manager")

logger.kill()
logger.configure(level=logging.INFO, handler=SparkTerminalHandler())

logger.info("Before context: only INFO and above are logged")

with TempLogLevel(logging.DEBUG):
    logger.debug("Inside context: DEBUG is now visible")
    logger.info("Inside context: INFO still visible")

logger.info("After context: back to INFO only")

# ---------------------------------------------------------------------------
# 10. TempLogLevel -- decorator
# ---------------------------------------------------------------------------
_section("10. TempLogLevel as a decorator")

logger.kill()
logger.configure(level=logging.INFO, handler=SparkTerminalHandler())


@TempLogLevel(logging.DEBUG)
def process_order(order_id: str) -> None:
    logger.debug("Processing order %s -- DEBUG visible via decorator", order_id)
    logger.info("Order %s accepted", order_id)


logger.info("Before decorated call: INFO only")
process_order("ORD-001")
logger.info("After decorated call: back to INFO only")

# ---------------------------------------------------------------------------
# 11. no_freeze + manual freeze()
# ---------------------------------------------------------------------------
_section("11. no_freeze=True followed by manual logger.freeze()")

logger.kill()
logger.configure(level=logging.DEBUG, no_freeze=True)
print(f"  frozen after configure(no_freeze=True): {logger.frozen}")

logger.freeze()
print(f"  frozen after logger.freeze():           {logger.frozen}")

logger.info("Works correctly after manual freeze")

# ---------------------------------------------------------------------------
# 12. Lifecycle state inspection
# ---------------------------------------------------------------------------
_section("12. Lifecycle state: is_configured and frozen properties")

logger.kill()
print(f"  Before configure: is_configured={logger.is_configured}, frozen={logger.frozen}")

logger.configure()
print(f"  After configure:  is_configured={logger.is_configured}, frozen={logger.frozen}")

logger.info("Lifecycle state confirmed")

# ---------------------------------------------------------------------------
# 13. FrozenClassException -- mutation after freeze
# ---------------------------------------------------------------------------
_section("13. FrozenClassException on mutation after freeze")

logger.kill()
logger.configure()

from logspark.Types.Exceptions import FrozenClassException

try:
    logger.addHandler(logging.StreamHandler())
except FrozenClassException as exc:
    print(f"  Caught expected FrozenClassException: {exc}")

# ---------------------------------------------------------------------------
# 14. SparkLogManager -- adopt + unify third-party loggers
# ---------------------------------------------------------------------------
_section("14. SparkLogManager: adopt a single logger, apply level + propagation")

logger.kill()
logger.configure()

noisy = logging.getLogger("some.library")
noisy.setLevel(logging.DEBUG)
noisy.addHandler(logging.StreamHandler())

print(f"  Before adopt: managed={spark_log_manager.managed_names}")

spark_log_manager.adopt(noisy)
print(f"  After adopt:  managed={spark_log_manager.managed_names}")

spark_log_manager.unify(level=logging.WARNING, propagate=False)
print(f"  After unify:  library level={noisy.level}, propagate={noisy.propagate}")

spark_log_manager.release("some.library")
print(f"  After release: managed={spark_log_manager.managed_names}")

# ---------------------------------------------------------------------------
# 15. SparkLogManager -- copy_spark_logger_config
# ---------------------------------------------------------------------------
_section("15. SparkLogManager: copy_spark_logger_config=True")

logger.kill()
logger.configure()

third_party = logging.getLogger("third_party_lib")
third_party.handlers.clear()

spark_log_manager.adopt(third_party)
spark_log_manager.unify(copy_spark_logger_config=True, propagate=False)

print(f"  third_party handler count: {len(third_party.handlers)}")
print(f"  third_party handlers:      {[type(h).__name__ for h in third_party.handlers]}")

third_party.warning("Third-party record routed through LogSpark handler")

spark_log_manager.release("third_party_lib")

# ---------------------------------------------------------------------------
# 16. adopt_all() -- batch-adopt all registered loggers
# ---------------------------------------------------------------------------
_section("16. SparkLogManager: adopt_all() + bulk silence")

logger.kill()
logger.configure()

import urllib.request  # noqa: F401 -- ensure urllib logger is registered

spark_log_manager.adopt_all(ignore=["third_party_lib"])
print(f"  Managed after adopt_all: {spark_log_manager.managed_names}")

spark_log_manager.unify(level=logging.WARNING)
spark_log_manager.release_all()

print(f"  Managed after release_all: {spark_log_manager.managed_names}")

# ---------------------------------------------------------------------------
print(f"\n{'=' * 62}")
print("  Demo complete")
print("=" * 62 + "\n")
