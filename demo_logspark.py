"""
LogSpark capabilities demo.

Run:  uv run python demo_logspark.py
Deps: logspark installed; `rich` and `python-json-logger` optional but recommended.
"""

import io
import logging
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from logspark import TempLogLevel, logger, spark_log_manager
from logspark.Handlers import SparkTerminalHandler
from logspark.Types import TracebackOptions
from logspark.Types.Options import PathResolutionSetting
import os

print(os.environ)

# ---------------------------------------------------------------------------
# ANSI helpers (work without Rich; safe to print alongside log output)
# ---------------------------------------------------------------------------
_TTY = sys.stdout.isatty() or True   # force colour in WezTerm even when piped

_R  = "\033[0m"
_B  = "\033[1m"
_D  = "\033[2m"
_CY = "\033[36m"
_GR = "\033[32m"
_YE = "\033[33m"
_RE = "\033[31m"
_MA = "\033[35m"
_BL = "\033[34m"
_WH = "\033[97m"


def _banner() -> None:
    print()
    print(f"  {_B}{_CY}╔══════════════════════════════════════════════════════════╗{_R}")
    print(f"  {_B}{_CY}║{_R}  {_B}{_WH}LogSpark{_R}  —  singleton logger with freeze semantics      {_B}{_CY}║{_R}")
    print(f"  {_B}{_CY}║{_R}  {_D}configure() → freeze() → use()  ·  kill() for isolation {_B}{_CY}║{_R}")
    print(f"  {_B}{_CY}╚══════════════════════════════════════════════════════════╝{_R}")
    print()


def _section(n: str, title: str, subtitle: str = "") -> None:
    width = 60
    bar = "━" * width
    sub = f"\n  {_D}{subtitle}{_R}" if subtitle else ""
    print(f"\n  {_B}{_BL}{bar}{_R}")
    print(f"  {_B}{_WH}{n}{_R}  {_B}{title}{_R}{sub}")
    print(f"  {_B}{_BL}{bar}{_R}\n")


def _note(msg: str) -> None:
    print(f"  {_D}↳ {msg}{_R}")


def _spacer() -> None:
    print()


# ---------------------------------------------------------------------------
# Probe optional dependencies once
# ---------------------------------------------------------------------------
try:
    from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler as _RichHandler
    from logspark.Types.Options import SparkRichHandlerSettings as _RichSettings
    _RICH = True
except Exception:
    _RICH = False

try:
    import pythonjsonlogger  # noqa: F401
    from logspark.Handlers import SparkJsonHandler as _JsonHandler
    _JSON = True
except Exception:
    _JSON = False

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
_banner()

# ===========================================================================
# 1 — Pre-configure: the logger is ready before you call configure()
# ===========================================================================
_section("01", "Pre-configure safety net",
         "Records logged before configure() are never silently dropped.")

_note("Logging without configure() — a one-time warning is emitted, output is preserved.")
_spacer()

logger.warning("app.startup: beginning service initialisation")
logger.info("app.startup: loading configuration from environment")

_spacer()
_note("SparkPreConfigHandler catches everything until configure() is called.")

# ===========================================================================
# 2 — configure() minimal: all five levels
# ===========================================================================
_section("02", "SparkTerminalHandler — all five levels",
         "ANSI color coding: gray DEBUG, white INFO, yellow WARNING, red ERROR, magenta CRITICAL.")

logger.kill()
logger.configure()

_note("Five log levels — one real-world message each.")
_spacer()

logger.debug("auth.token: cache miss — fetching from identity service")
logger.info("http.server: GET /api/v1/orders/ORD-8821 → 200 OK  [14 ms]")
logger.warning("db.pool: connection pool at 87%% capacity (43/50 used)")
logger.error("payment.stripe: charge failed — card_declined for customer cust_9KQx")
logger.critical("db.primary: connection lost — initiating failover to replica")

# ===========================================================================
# 3 — Traceback policies: COMPACT / FULL / HIDE
# ===========================================================================
_section("03", "Traceback policies",
         "COMPACT = type + message + single frame  ·  FULL = all frames  ·  HIDE = type + message only")


def _nested_failure() -> None:
    """Simulates a real call chain so FULL shows multiple frames."""
    _parse_payload(b"\xff\xfe invalid utf-8")


def _parse_payload(raw: bytes) -> str:
    return raw.decode("utf-8")


# --- 3a COMPACT (default) ---------------------------------------------------
logger.kill()
logger.configure(traceback_policy=TracebackOptions.COMPACT)

_note("COMPACT: enough context to locate the bug, no traceback noise.")
_spacer()

try:
    _nested_failure()
except UnicodeDecodeError:
    logger.exception("ingest.parser: failed to decode incoming payload")

_spacer()

# --- 3b FULL ----------------------------------------------------------------
logger.kill()
logger.configure(traceback_policy=TracebackOptions.FULL)

_note("FULL: every frame — for deep post-mortem debugging.")
_spacer()

try:
    _nested_failure()
except UnicodeDecodeError:
    logger.exception("ingest.parser: full traceback for incident investigation")

_spacer()

# --- 3c HIDE ----------------------------------------------------------------
logger.kill()
logger.configure(traceback_policy=TracebackOptions.HIDE)

_note("HIDE: exception type + message only — safe for user-facing pipelines.")
_spacer()

try:
    raise PermissionError("user uid=4412 not authorised for resource /admin/billing")
except PermissionError:
    logger.exception("auth.middleware: access denied — no internal details leaked")

# ===========================================================================
# 4 — Path resolution modes
# ===========================================================================
_section("04", "Path resolution settings",
         "FILE = filename only  ·  RELATIVE = project-relative (default)  ·  ABSOLUTE = full path")

for mode, label in (
    (PathResolutionSetting.FILE,     "FILE     — filename only"),
    (PathResolutionSetting.RELATIVE, "RELATIVE — relative to project root  (default)"),
    (PathResolutionSetting.ABSOLUTE, "ABSOLUTE — full filesystem path"),
):
    logger.kill()
    logger.configure(path_resolution=mode)
    _note(label)
    logger.info("jobs.scheduler: nightly report job queued  [run_id=RUN-20240315]")

# ===========================================================================
# 5 — Structured data via extra=
# ===========================================================================
_section("05", "Structured context via extra=",
         "Any keyword arguments in extra= are forwarded unchanged to handlers and formatters.")

logger.kill()
logger.configure()

_note("HTTP request lifecycle — structured fields attached at each stage.")
_spacer()

logger.info(
    "http.request: accepted",
    extra={"method": "POST", "path": "/api/v1/checkout", "client_ip": "203.0.113.42"},
)
logger.info(
    "payment.stripe: charge authorised",
    extra={"amount_cents": 4999, "currency": "USD", "card_last4": "4242", "latency_ms": 87},
)
logger.warning(
    "db.query: slow query detected",
    extra={"table": "order_items", "duration_ms": 1340, "threshold_ms": 500},
)
logger.error(
    "http.response: 500 Internal Server Error",
    extra={"request_id": "req_7fGHk2", "duration_ms": 1427, "retries": 3},
)

# ===========================================================================
# 6 — TempLogLevel: context manager
# ===========================================================================
_section("06", "TempLogLevel — scoped debug window",
         "Lowers the effective log level for a block; the original level is restored on exit.")

logger.kill()
logger.configure(level=logging.INFO, handler=SparkTerminalHandler())

_note("Investigating a slow checkout — temporarily open DEBUG without touching the handler.")
_spacer()

logger.info("checkout.api: received checkout request  [session=sess_Xk9Qr]")
logger.debug("checkout.api: DEBUG suppressed outside context (level=INFO)")

with TempLogLevel(logging.DEBUG):
    logger.debug("checkout.steps: [1/4] validating cart items")
    logger.debug("checkout.steps: [2/4] checking inventory — 3 items verified")
    logger.debug("checkout.steps: [3/4] applying promo code SAVE20 — -$12.00")
    logger.debug("checkout.steps: [4/4] submitting payment authorisation")
    logger.info("checkout.api: checkout completed successfully")

logger.debug("checkout.api: DEBUG suppressed again (level restored to INFO)")
logger.info("checkout.api: session closed  [sess_Xk9Qr]")

# ===========================================================================
# 7 — TempLogLevel: decorator
# ===========================================================================
_section("07", "TempLogLevel — function decorator",
         "Wraps a function so DEBUG is active for every call; zero boilerplate at the call site.")

logger.kill()
logger.configure(level=logging.INFO, handler=SparkTerminalHandler())


@TempLogLevel(logging.DEBUG)
def process_refund(order_id: str, amount_cents: int) -> None:
    logger.debug("refund.worker: validating refund eligibility  [order=%s]", order_id)
    logger.debug("refund.worker: contacting payment gateway")
    logger.info("refund.worker: refund of $%.2f issued  [order=%s]", amount_cents / 100, order_id)


logger.info("worker.queue: picked up 2 refund tasks")
process_refund("ORD-8819", 2999)
process_refund("ORD-8820", 4500)
logger.info("worker.queue: refund batch complete")

# ===========================================================================
# 8 — no_freeze + addHandler + manual freeze
# ===========================================================================
_section("08", "no_freeze=True — multi-handler configuration",
         "configure(no_freeze=True) leaves the logger mutable; call freeze() when setup is done.")

logger.kill()
logger.configure(level=logging.DEBUG, no_freeze=True)

_note(f"frozen={logger.frozen} after configure(no_freeze=True) — handlers can still be added.")

terminal_buf = io.StringIO()
logger.addHandler(SparkTerminalHandler(stream=terminal_buf))

logger.freeze()
_note(f"frozen={logger.frozen} after logger.freeze() — configuration locked.")

logger.warning("ops.deploy: deployment pipeline started  [build=v1.4.2-rc3]")
logger.error("ops.deploy: smoke test failed on node web-03 — rolling back")
logger.info("ops.deploy: rollback complete — web-03 restored to v1.4.1")

_spacer()
_note(f"terminal_buf captured {len(terminal_buf.getvalue().splitlines())} lines via second handler.")

# ===========================================================================
# 9 — FrozenClassException
# ===========================================================================
_section("09", "FrozenClassException — immutability after freeze",
         "Once frozen, addHandler() / addFilter() / eject_handlers() all raise FrozenClassException.")

from logspark.Types import FrozenClassException  # noqa: E402

logger.kill()
logger.configure()

_note("Attempting to add a handler to a frozen logger:")
_spacer()

try:
    logger.addHandler(logging.StreamHandler())
except FrozenClassException as exc:
    print(f"  {_RE}{_B}FrozenClassException{_R}{_RE}: {exc}{_R}")

_spacer()
_note("Attempting to eject handlers from a frozen logger:")
_spacer()

try:
    logger.eject_handlers()
except FrozenClassException as exc:
    print(f"  {_RE}{_B}FrozenClassException{_R}{_RE}: {exc}{_R}")

# ===========================================================================
# 10 — SparkLogManager: tame noisy third-party loggers
# ===========================================================================
_section("10", "SparkLogManager — third-party logger control",
         "adopt() / adopt_all() snapshot loggers; unify() applies batch mutations.")

logger.kill()
logger.configure()

# Simulate a noisy third-party library hierarchy
for name in ("urllib3.connectionpool", "requests.packages.urllib3", "boto3", "botocore.endpoint"):
    lg = logging.getLogger(name)
    lg.setLevel(logging.DEBUG)
    lg.addHandler(logging.StreamHandler())

_note("Before unify: third-party loggers at DEBUG with their own StreamHandlers.")
_spacer()
print(f"  {'Logger':<40} {'level':>6}  handlers")
print(f"  {'──────':<40} {'─────':>6}  ────────")
for name in ("urllib3.connectionpool", "requests.packages.urllib3", "boto3", "botocore.endpoint"):
    lg = logging.getLogger(name)
    print(f"  {_D}{name:<40}{_R}  {_YE}{logging.getLevelName(lg.level):>6}{_R}  {len(lg.handlers)}")

spark_log_manager.adopt_all(ignore=["urllib3"])
_spacer()
_note(f"adopt_all() snapshot: {len(spark_log_manager.managed_names)} loggers managed.")

spark_log_manager.unify(
    level=logging.WARNING,
    handlers=[SparkTerminalHandler(stream=io.StringIO())],
    propagate=False,
)
_spacer()
_note("After unify(level=WARNING, handlers=[SparkTerminalHandler], propagate=False):")
_spacer()
print(f"  {'Logger':<40} {'level':>6}  handlers")
print(f"  {'──────':<40} {'─────':>6}  ────────")
for name in ("requests.packages.urllib3", "boto3", "botocore.endpoint"):
    lg = logging.getLogger(name)
    hnames = [type(h).__name__ for h in lg.handlers]
    print(f"  {_D}{name:<40}{_R}  {_GR}{logging.getLevelName(lg.level):>6}{_R}  {hnames}")

spark_log_manager.release_all()
_note(f"After release_all(): managed={spark_log_manager.managed_names}")

# ===========================================================================
# 11 — SparkLogManager: copy_spark_logger_config
# ===========================================================================
_section("11", "SparkLogManager — copy_spark_logger_config=True",
         "Copies handlers and filters from the frozen LogSpark logger to all managed loggers.")

logger.kill()
logger.configure()

db_logger = logging.getLogger("sqlalchemy.engine")
db_logger.handlers.clear()

spark_log_manager.adopt(db_logger)
spark_log_manager.unify(copy_spark_logger_config=True, level=logging.WARNING, propagate=False)

_note(f"sqlalchemy.engine now shares LogSpark's handler: {[type(h).__name__ for h in db_logger.handlers]}")
_spacer()

db_logger.warning("sqlalchemy.engine: slow query  [duration=2.3s  table=order_items]")
db_logger.error("sqlalchemy.engine: pool timeout — all 10 connections in use")

spark_log_manager.release("sqlalchemy.engine")

# ===========================================================================
# 12 — SparkJsonHandler: structured single-line JSON output
# ===========================================================================
if _JSON:
    _section("12", "SparkJsonHandler — structured JSON output",
             "One JSON object per record, single-line invariant, traceback policy applied.")

    logger.kill()

    try:
        buf = io.StringIO()
        json_handler = _JsonHandler(stream=buf)
        logger.configure(handler=json_handler)

        logger.info(
            "api.gateway: request routed",
            extra={"service": "checkout", "region": "eu-west-1", "latency_ms": 31},
        )
        logger.warning(
            "cache.redis: eviction rate above threshold",
            extra={"eviction_rate": 0.34, "threshold": 0.20, "keys_evicted": 1847},
        )

        try:
            raise ConnectionRefusedError("redis://cache-01:6379 — connection refused")
        except ConnectionRefusedError:
            logger.exception("cache.redis: fallback to in-process cache")

        _note("Raw JSON output (one record per line):")
        _spacer()
        for line in buf.getvalue().strip().splitlines():
            print(f"  {_D}{line}{_R}")

    except Exception as exc:
        _note(f"SparkJsonHandler unavailable: {exc}")
else:
    _section("12", "SparkJsonHandler — skipped (python-json-logger not installed)", "")

# ===========================================================================
# 13 — SparkRichHandler: full column layout
# ===========================================================================
if _RICH:
    _section("13", "SparkRichHandler — Rich column layout",
             "Time · Level · Message · Path  —  budget-based, terminal-adaptive.")

    logger.kill()

    settings = _RichSettings(
        min_message_width=45,
        max_path_width=30,
        max_function_width=22,
        omit_repeated_times=False,
        enable_link_path=True,
        indent_guide="|",
    )
    rich_handler = _RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        show_function=True,
        traceback_policy=TracebackOptions.COMPACT,
        settings=settings,
    )
    logger.configure(handler=rich_handler)

    logger.debug("worker.pool: spawning 4 worker threads")
    logger.info("api.server: listening on 0.0.0.0:8080")
    logger.info(
        "http.request: POST /api/v1/orders",
        extra={"user_id": "usr_4Ek9Q", "items": 3, "total_cents": 7499},
    )
    logger.warning("db.pool: connection pool at 92%% capacity  [44/50]")
    logger.error(
        "payment.provider: charge declined",
        extra={"code": "insufficient_funds", "customer": "cust_Xk9Qr"},
    )

    _spacer()
    _note("With COMPACT traceback policy:")
    _spacer()

    try:
        raise ValueError("order total mismatch: expected 7499 got 7350")
    except ValueError:
        logger.exception("checkout.validator: order integrity check failed")

    logger.kill()

    _note("With HIDE policy — no location, no stack, exception type + message only:")
    _spacer()

    hide_settings = _RichSettings(min_message_width=45, max_path_width=30)
    logger.configure(
        handler=_RichHandler(traceback_policy=TracebackOptions.HIDE, settings=hide_settings)
    )

    try:
        raise PermissionError("user uid=4412 cannot access resource /admin/billing")
    except PermissionError:
        logger.exception("auth.policy: access denied — internal detail suppressed")

else:
    _section("13", "SparkRichHandler — skipped (rich not installed)", "")

# ===========================================================================
# 14 — Lifecycle inspection
# ===========================================================================
_section("14", "Lifecycle state properties",
         "is_configured and frozen reflect the exact configuration stage.")

logger.kill()
print(f"  {_D}After kill():{_R}")
print(f"    is_configured = {_YE}{logger.is_configured}{_R}")
print(f"    frozen        = {_YE}{logger.frozen}{_R}")

logger.configure(no_freeze=True)
print(f"\n  {_D}After configure(no_freeze=True):{_R}")
print(f"    is_configured = {_GR}{logger.is_configured}{_R}")
print(f"    frozen        = {_YE}{logger.frozen}{_R}")

logger.freeze()
print(f"\n  {_D}After freeze():{_R}")
print(f"    is_configured = {_GR}{logger.is_configured}{_R}")
print(f"    frozen        = {_GR}{logger.frozen}{_R}")

logger.info("api.server: all systems operational")

# ===========================================================================
# Footer
# ===========================================================================
logger.kill()
print()
print(f"  {_B}{_CY}╔══════════════════════════════════════════════════════════╗{_R}")
print(f"  {_B}{_CY}║{_R}  {_B}{_GR}14 sections complete.{_R}  LogSpark demo finished.             {_B}{_CY}║{_R}")
rich_line  = f"  {_B}{_CY}║{_R}  {_D}Rich:        {'available' if _RICH else 'not installed — pip install rich':}{_R}"
json_line  = f"  {_B}{_CY}║{_R}  {_D}JSON logger: {'available' if _JSON else 'not installed — pip install python-json-logger':}{_R}"
print(f"{rich_line:<70}{_B}{_CY}║{_R}")
print(f"{json_line:<70}{_B}{_CY}║{_R}")
print(f"  {_B}{_CY}╚══════════════════════════════════════════════════════════╝{_R}")
print()
