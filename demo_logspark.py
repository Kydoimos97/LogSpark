"""LogSpark demo — compact showcase for README screenshot.

Run:  task run-demo
Deps: logspark[all]
"""

import io
import logging
import os
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import warnings
warnings.filterwarnings("ignore")

from logspark import TempLogLevel, logger, spark_log_manager
from logspark.Handlers import SparkJsonHandler, SparkTerminalHandler
from logspark.Types import TracebackOptions
from logspark.Types.Options import PathResolutionSetting

try:
    from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
    from logspark.Types.Options import SparkRichHandlerSettings
    _RICH = True
except Exception:
    _RICH = False

_D = "\033[2m"
_R = "\033[0m"
_B = "\033[1m"
_CY = "\033[36m"
_GR = "\033[32m"
_YE = "\033[33m"

def _hr(label: str) -> None:
    pad = 64 - len(label) - 2
    print(f"\n{_D}── {label} {'─' * pad}{_R}")


def _nested_call() -> None:
    _decode(b"\xff\xfe invalid utf-8")


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8")


# ── Rich handler: all levels + exception + TempLogLevel ─────────────────────
if _RICH:
    _hr("SparkRichHandler · all levels · COMPACT traceback · TempLogLevel")

    settings = SparkRichHandlerSettings(
        min_message_width=40,
        max_path_width=22,
        omit_repeated_times=False,
        enable_link_path=False,
    )
    rich_h = SparkRichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        show_function=False,
        traceback_policy=TracebackOptions.COMPACT,
        settings=settings,
    )
    logger.kill()
    logger.configure(level=logging.DEBUG, handler=rich_h)

    logger.debug("worker.pool: spawning 4 threads  [cpu=8  pid=%d]", os.getpid())
    logger.info("api.server: listening on 0.0.0.0:8080")
    logger.info("http.request: POST /api/v1/checkout  [user=usr_4Ek9  $74.99]")
    logger.warning("db.pool: 92%% capacity  [44/50 connections used]")
    logger.error("payment.stripe: card_declined  [cust_Xk9Q  $74.99]")
    logger.critical("db.primary: connection lost — failover to replica initiated")

    try:
        _nested_call()
    except UnicodeDecodeError:
        logger.exception("ingest.parser: failed to decode payload")

    _hr("TempLogLevel — scoped debug window  [context manager + decorator]")

    _tl_handler = SparkRichHandler(
        show_time=True, show_level=True, show_path=True, show_function=False,
        traceback_policy=TracebackOptions.COMPACT,
        settings=SparkRichHandlerSettings(min_message_width=40, max_path_width=22),
    )
    logger.kill()
    logger.configure(level=logging.INFO, handler=_tl_handler)
    _tl_handler.setLevel(logging.NOTSET)

    logger.info("checkout.api: order received  [session=sess_Xk9Qr]")
    logger.debug("checkout.api: suppressed — level=INFO outside context")
    with TempLogLevel(logging.DEBUG):
        logger.debug("checkout.steps: [1/4] cart validated  [3 items]")
        logger.debug("checkout.steps: [2/4] inventory ok  [all in stock]")
        logger.debug("checkout.steps: [3/4] promo SAVE20 applied  [-$12.00]")
        logger.debug("checkout.steps: [4/4] payment authorised")
    logger.debug("checkout.api: suppressed — level restored to INFO")
    logger.info("checkout.api: order complete  [order=ORD-9921  total=$62.99]")

# ── SparkTerminalHandler fallback (if Rich not available) ────────────────────
else:
    _hr("SparkTerminalHandler · all levels · COMPACT traceback")
    logger.kill()
    logger.configure(level=logging.DEBUG, traceback_policy=TracebackOptions.COMPACT)
    logger.debug("worker.pool: spawning 4 threads")
    logger.info("api.server: listening on 0.0.0.0:8080")
    logger.warning("db.pool: 92%% capacity  [44/50]")
    logger.error("payment.stripe: card_declined  [customer=cust_Xk9Q]")
    logger.critical("db.primary: connection lost — failover initiated")
    try:
        _nested_call()
    except UnicodeDecodeError:
        logger.exception("ingest.parser: failed to decode payload")

# ── Rich handler: level_width abbreviation cascade ──────────────────────────
if _RICH:
    _hr("SparkRichHandler · level_width abbreviation cascade")

    from rich.console import Console

    _LEVEL_WIDTHS = [2, 4, 6, 8]
    _DEMO_WIDTH = 100

    for _lw in _LEVEL_WIDTHS:
        _lw_console = Console(width=_DEMO_WIDTH, no_color=False, highlight=True)
        _lw_settings = SparkRichHandlerSettings(
            min_message_width=40,
            max_path_width=22,
            omit_repeated_times=False,
            enable_link_path=False,
            level_width=_lw,
        )
        _lw_handler = SparkRichHandler(
            console=_lw_console,
            show_time=True,
            show_level=True,
            show_path=True,
            show_function=False,
            traceback_policy=TracebackOptions.COMPACT,
            settings=_lw_settings,
        )
        logger.kill()
        logger.configure(level=logging.DEBUG, handler=_lw_handler)
        _lw_handler.setLevel(logging.NOTSET)

        print(f"  {_D}level_width={_lw}{_R}")
        logger.debug("worker.pool: spawning threads  [level_width=%d]", _lw)
        logger.warning("db.pool: 92%% capacity  [44/50 connections used]")
        logger.critical("db.primary: connection lost — failover initiated")

    logger.kill()

# ── SparkJsonHandler ─────────────────────────────────────────────────────────
_hr("SparkJsonHandler · structured single-line JSON · traceback policy applied")

logger.kill()
buf = io.StringIO()
logger.configure(handler=SparkJsonHandler(stream=buf))

logger.info("api.gateway: request routed", extra={"service": "checkout", "region": "eu-west-1", "latency_ms": 31})
logger.warning("cache.redis: eviction above threshold", extra={"eviction_rate": 0.34, "keys_evicted": 1847})
try:
    raise ConnectionRefusedError("redis://cache-01:6379 — connection refused")
except ConnectionRefusedError:
    logger.exception("cache.redis: falling back to in-process cache")

for line in buf.getvalue().strip().splitlines():
    print(f"  {_D}{line}{_R}")

# ── SparkLogManager ──────────────────────────────────────────────────────────
_hr("SparkLogManager · adopt_all · unify · release_all")

logger.kill()
logger.configure()

for name in ("urllib3", "httpx", "sqlalchemy.engine", "boto3"):
    lg = logging.getLogger(name)
    lg.setLevel(logging.DEBUG)
    lg.addHandler(logging.StreamHandler())

spark_log_manager.adopt_all()
before = {n: (logging.getLevelName(logging.getLogger(n).level), len(logging.getLogger(n).handlers))
          for n in ("urllib3", "httpx", "sqlalchemy.engine", "boto3")}

spark_log_manager.unify(level=logging.WARNING, handlers=[SparkTerminalHandler(stream=io.StringIO())], propagate=False)
after = {n: (logging.getLevelName(logging.getLogger(n).level), [type(h).__name__ for h in logging.getLogger(n).handlers])
         for n in ("urllib3", "httpx", "sqlalchemy.engine", "boto3")}

print(f"  {_D}{'logger':<24} {'before':>18}   {'after'}{_R}")
print(f"  {_D}{'──────':<24} {'──────':>18}   {'─────'}{_R}")
for n in ("urllib3", "httpx", "sqlalchemy.engine", "boto3"):
    b_lvl, b_h = before[n]
    a_lvl, a_h = after[n]
    print(f"  {n:<24} {_YE}{b_lvl:>8}{_R} {b_h}h  →  {_GR}{a_lvl:>8}{_R} {a_h}")

spark_log_manager.release_all()

# ── Lifecycle state ──────────────────────────────────────────────────────────
_hr("Lifecycle · configure → freeze → kill")

logger.kill()
states = []
states.append(("kill()", logger.is_configured, logger.frozen))
logger.configure(no_freeze=True)
states.append(("configure(no_freeze=True)", logger.is_configured, logger.frozen))
logger.freeze()
states.append(("freeze()", logger.is_configured, logger.frozen))

for label, cfg, frz in states:
    cfg_c = _GR if cfg else _YE
    frz_c = _GR if frz else _YE
    print(f"  {_D}{label:<28}{_R}  is_configured={cfg_c}{cfg}{_R}  frozen={frz_c}{frz}{_R}")

print()
