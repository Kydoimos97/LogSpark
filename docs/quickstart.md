# Quickstart

## Installation

```bash
pip install logspark
```

For Rich terminal output (recommended for development):

```bash
pip install logspark[color]
```

---

## Minimal setup

```python
from logspark import logger

logger.configure()

logger.info("Logger is ready")
```

That is a complete, production-safe setup. `configure()` with no arguments gives you:

- Terminal output to stdout
- `INFO` level and above
- Color output if your terminal supports it
- Compact tracebacks on exceptions
- Relative file paths in log lines

---

## Setting the level

```python
import logging
from logspark import logger

logger.configure(level=logging.DEBUG)
```

Standard stdlib level constants work directly. String names also work:

```python
logger.configure(level="DEBUG")
```

---

## Logging exceptions

Call `logger.exception()` from inside an `except` block. It logs at `ERROR` level and captures the current exception automatically:

```python
try:
    result = 1 / 0
except ZeroDivisionError:
    logger.exception("Calculation failed")
```

The traceback policy controls how much of the exception appears in output. See [Output Modes: Traceback policy](output-modes.md#traceback-policy).

---

## Logging structured data

Pass a dict to `extra` to attach key-value fields to a log record. In terminal output these are available for formatting; in JSON output they appear as top-level keys:

```python
logger.info("Request completed", extra={
    "method": "GET",
    "path": "/api/users",
    "status": 200,
    "duration_ms": 42,
})
```

---

## Where to call configure()

At process startup, before any other module uses the logger:

```python
# main.py or entrypoint
import logging
from logspark import logger

logger.configure(level=logging.INFO)

from myapp import run
run()
```

If you log before `configure()`, LogSpark will not silently discard the record. It logs with a minimal fallback format and emits a warning. See [Lifecycle: Before configure() is called](lifecycle.md#before-configure-is-called).

---

## Next steps

- [Concepts](concepts.md): How the pipeline fits together and where LogSpark sits in it
- [Lifecycle](lifecycle.md): Why `configure()` runs once and what freeze means
- [Output Modes](output-modes.md): Terminal vs JSON, traceback policy, path resolution
