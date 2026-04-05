# Scoped log levels

`TempLogLevel` temporarily changes the logger's effective level for a block of code or a function, then restores it automatically. It does not touch the [frozen configuration](lifecycle.md#freeze). Handlers and filters are unchanged.

Use this when you need debug output from a specific path without lowering the level globally.

## As a context manager

```python
import logging
from logspark import logger, TempLogLevel
from logspark.Handlers import SparkTerminalHandler

# Pass an explicit handler with the default level (NOTSET) so the logger
# level alone controls the minimum.  When configure() creates a default
# handler it sets the handler level equal to the logger level, which would
# block the debug records TempLogLevel is intended to expose.
logger.configure(level=logging.INFO, handler=SparkTerminalHandler())

logger.info("before context: only INFO and above")

with TempLogLevel(logging.DEBUG):
    logger.debug("inside context: DEBUG is now visible")
    logger.info("inside context: INFO still visible")

logger.info("after context: back to INFO only")
```

## As a decorator

```python
import logging
from logspark import logger, TempLogLevel
from logspark.Handlers import SparkTerminalHandler

logger.configure(level=logging.INFO, handler=SparkTerminalHandler())

@TempLogLevel(logging.DEBUG)
def process_payment(order_id: str):
    logger.debug("Processing payment for order %s", order_id)
    logger.info("Payment accepted for order %s", order_id)
```

Every call to `process_payment()` runs with `DEBUG` level. The original level is restored after each call, including if the function raises.

## What it does not do

- Does not affect handler-level filtering. `TempLogLevel` lowers the *logger* level only. If the handler has a level set (e.g. the default `configure()` handler is created with the same level as the logger), records still pass through the handler's own level check. Pass `handler=SparkTerminalHandler()` (no explicit level) to let the logger level alone control filtering.
- Does not affect other loggers, only the LogSpark `logger` singleton.
- Does not modify frozen configuration. It is an intentional escape hatch, not a workaround for the freeze.

---