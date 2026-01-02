<div align="center">
<img alt="Logo.png" src="assets/Logo.png" width="250" height="250"/>
</div>


**Drop-in logging foundation** for Python projects.

LogSpark gives you sane logging defaults that work immediately, with no decisions required. It composes battle-tested systems (stdlib logging, Rich, python-json-logger) instead of replacing them.

## Get Started in 30 Seconds

```python
from logspark import spark_logger
import logging

spark_logger.configure(level=logging.INFO, preset="terminal")

spark_logger.info("Application started")
spark_logger.error("Something went wrong")
```

You now have:

- Terminal output with colors and structure
- Automatic Rich formatting when available
- Immutable configuration that prevents drift
- Full compatibility with existing stdlib logging code

## Why This Exists

Most Python projects copy-paste logging setup across modules, leading to:

```python
# Module A
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Module B  
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
# Different format, order-dependent setup, configuration drift
```

LogSpark eliminates this by providing:

- **One configuration point** that works everywhere
- **Immutable behavior** after setup (no drift)
- **Stable identity** in deep stacks (tests, frameworks, dependencies)
- **Hardened integrations** with Rich, JSON logging, and distributed tracing

## No Lock-In by Design

Every component works independently:

```python
# Use handlers without the singleton
import logging
from logspark.Handlers import TerminalHandler

logger = logging.getLogger("myapp")
logger.addHandler(TerminalHandler(show_time=True))
```

```python
# Add filters to existing loggers
from logspark.Filters import DDTraceCorrelationFilter

existing_handler.addFilter(DDTraceCorrelationFilter())
```

```python
# Global control when you need it
from logspark import spark_log_manager

spark_log_manager.adopt_all()  # Snapshot existing loggers
spark_log_manager.unify(use_spark_handler=True)  # Apply consistent formatting
```

You can adopt LogSpark incrementally: handlers first, then logger, then global control. Or use any piece independently.

## Production Ready

```python
# Structured JSON for log aggregation
spark_logger.configure(level=logging.INFO, preset="json")

spark_logger.info("User login", extra={"user_id": 123, "ip": "192.168.1.1"})
# Output: {"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "message": "User login", "user_id": 123, "ip": "192.168.1.1"}
```

**Guarantees**:

- Single-line JSON output (tracebacks compacted)
- Automatic correlation fields when ddtrace is active
- No ANSI codes or formatting artifacts
- Consistent schema across all services

## Install

```bash
pip install logspark

# Optional features
pip install logspark[json]    # JSON structured logging  
pip install logspark[color]   # Rich terminal colors
pip install logspark[trace]   # DDTrace integration
```