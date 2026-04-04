<div align="center">
<img alt="LogSpark" src="https://raw.githubusercontent.com/Kydoimos97/LogSpark/main/docs/assets/Logo.png" width="200" height="200"/>
</div>

<p align="center">
  <a href="https://github.com/Kydoimos97/logspark/actions/workflows/run-tests.yml">
    <img src="https://github.com/Kydoimos97/logspark/actions/workflows/run-tests.yml/badge.svg" alt="Tests">
  </a>
  <a href="https://codecov.io/gh/Kydoimos97/logspark">
    <img src="https://codecov.io/gh/Kydoimos97/logspark/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/logspark/">
    <img src="https://img.shields.io/pypi/v/logspark.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/logspark/">
    <img src="https://img.shields.io/pypi/pyversions/logspark.svg" alt="Python 3.11+">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  </a>
</p>

<p align="center"><b>
Drop-in logging foundation for Python projects.
</b></p>

<p align="center">
  <a href="https://logspark.readthedocs.io/en/latest/"><b>Documentation</b></a>
</p>

---

LogSpark is a configuration and integration layer over Python's standard `logging` module. It adds lifecycle enforcement, environment-aware output policy, and corrected defaults — without replacing stdlib logging or introducing a new API. Every handler, filter, and formatter is a plain stdlib object.

<div align="center">
<img alt="LogSpark Demo" src="https://raw.githubusercontent.com/Kydoimos97/LogSpark/main/docs/assets/demo_log.png" width="1000" height="604"/>
</div>

---

## Installation

```bash
pip install logspark
```

Optional extras:

```bash
pip install logspark[color]   # Rich terminal output with layout and color
pip install logspark[json]    # Structured single-line JSON output
pip install logspark[trace]   # Datadog DDTrace correlation injection
pip install logspark[all]     # All of the above
```

---

## Quick Start

### Minimal setup

```python
from logspark import logger

logger.configure()
logger.info("Application started")
```

`configure()` with no arguments gives you terminal output to stdout, INFO level and above, color if your terminal supports it, compact tracebacks, and relative file paths in log lines.

### Set the log level

```python
import logging
from logspark import logger

logger.configure(level=logging.DEBUG)
```

Standard stdlib level constants and string names both work.

### Log exceptions

```python
try:
    result = 1 / 0
except ZeroDivisionError:
    logger.exception("Calculation failed")
```

### Attach structured fields

```python
logger.info("Request completed", extra={
    "method": "GET",
    "path": "/api/users",
    "status": 200,
    "duration_ms": 42,
})
```

### JSON output

```python
import logging
from logspark import logger
from logspark.Handlers import SparkJsonHandler

logger.configure(level=logging.INFO, handler=SparkJsonHandler())
logger.info("Structured record", extra={"env": "production"})
```

### Rich terminal output

```python
import logging
from logspark import logger
from logspark.Handlers.Rich import SparkRichHandler

logger.configure(level=logging.DEBUG, handler=SparkRichHandler())
logger.debug("Rich layout with columns, color, and path resolution")
```

### Silence or unify third-party loggers

```python
import logging
import httpx
from logspark import logger, spark_log_manager

logger.configure()

spark_log_manager.adopt_all()
spark_log_manager.unify(
    copy_spark_logger_config=True,
    level=logging.WARNING,
    propagate=False,
)
```

### Scoped debug level

```python
import logging
from logspark import logger, TempLogLevel
from logspark.Handlers import SparkTerminalHandler

logger.configure(level=logging.INFO, handler=SparkTerminalHandler())

with TempLogLevel(logging.DEBUG):
    logger.debug("Visible only inside this block")
```

---

## Key features

| Feature | Description |
|---|---|
| Lifecycle enforcement | `configure -> freeze -> use`: configuration happens once, explicitly |
| Output modes | Terminal with color or JSON, switchable via environment variable |
| Traceback control | Hide, compact, or full tracebacks per-logger |
| Scoped debugging | Temporarily lower the log level for a block without changing config |
| Third-party management | Suppress or unify noisy loggers without touching their source |
| stdlib compatibility | Every component works standalone with any `logging.Logger` |

---

## Where to call configure()

At process startup, before any other module uses the logger:

```python
# main.py
import logging
from logspark import logger

logger.configure(level=logging.INFO)

from myapp import run
run()
```

If a log record is emitted before `configure()`, LogSpark uses a minimal fallback format and emits a one-time warning. It does not silently discard records.

---

## Documentation

- [Quickstart](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [Lifecycle](docs/lifecycle.md)
- [Output Modes](docs/output-modes.md)
- [Environment Variables](docs/environment.md)
- [Advanced Usage](docs/advanced.md)
- [Component Reference](docs/reference.md)

---

## License

MIT — see [LICENSE](LICENSE) for details.