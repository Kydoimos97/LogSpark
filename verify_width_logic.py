"""Width layout verification script.

Shows how SparkRichHandler column layout changes at different terminal widths.
Each width gets the same set of log records so behaviour is directly comparable.

Run:  uv run python verify_width_logic.py
"""

import io
import logging
import sys
import warnings


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console

from logspark import logger
from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
from logspark.Types import TracebackOptions
from logspark.Types.Options import SparkRichHandlerSettings

warnings.filterwarnings("ignore", category=UserWarning)

WIDTHS = [200, 120, 80, 60, 40]
LEVEL_WIDTHS = [2, 4, 6, 8, 20]

SETTINGS = SparkRichHandlerSettings(
    min_message_width=40,
    max_path_width=30,
    max_function_width=20,
    omit_repeated_times=False,
    enable_link_path=False,
    level_width=9,

)


def _make_handler(width: int, level_width: int) -> SparkRichHandler:
    console = Console(width=width, no_color=False, highlight=True)
    settings = SETTINGS
    settings.level_width = level_width
    return SparkRichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        show_function=False,
        traceback_policy=TracebackOptions.COMPACT,
        settings=settings
    )


def _run_records(width: int, level_width: int) -> None:
    handler = _make_handler(width, level_width)

    logger.kill()
    logger.configure(level=logging.DEBUG, handler=handler)
    handler.setLevel(logging.NOTSET)

    # logger.debug("cache miss — fetching token from identity service")
    # logger.info("GET /api/v1/orders/ORD-8821 responded 200 OK in 14ms | level_width=%d", level_width)
    # logger.warning("db.pool at 87%% capacity  [43/50 connections used]")
    # logger.error("payment.stripe: card_declined for customer cust_9KQx")
    logger.critical("db.primary: connection lost — initiating failover")

    try:
        raise ValueError("order total mismatch: expected 7499 got 7350")
    except ValueError:
        logger.exception("checkout.validator: order integrity check failed")

    logger.kill()
    return


def _separator(width: int, label: str) -> None:
    bar = "─" * 64
    print(f"\n{bar}")
    print(f"  width={width}  —  {label}")
    print(f"{bar}\n")


def main() -> None:
    for width in WIDTHS:
        if width >= 120:
            label = "all columns visible"
        elif width >= 80:
            label = "function may drop"
        elif width >= 60:
            label = "path may drop"
        else:
            label = "degraded — message only"

        _separator(width, label)
        for lwidth in LEVEL_WIDTHS:
            _run_records(width, lwidth)


if __name__ == "__main__":
    main()
