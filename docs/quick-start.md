# Quick Start

Get LogSpark running in your project with these complete examples.

## 1. Drop-In Foundation (Recommended)

Replace scattered logging setup with one configuration:

```python
from logspark import spark_logger
import logging

spark_logger.configure(level=logging.INFO, preset="terminal")

spark_logger.info("Application started")
spark_logger.warning("Something looks odd")
spark_logger.error("Failed to process request", extra={"user_id": 123})
```

**What you get**:

- Human-readable terminal output with colors and structure
- Rich formatting when available, graceful fallback when not
- Immutable configuration (no drift)
- Standard logging methods everywhere

## 2. Production JSON Logging

Structured output for log aggregation and monitoring:

```python
spark_logger.configure(level=logging.INFO, preset="json")

spark_logger.info("User login", extra={"user_id": 123, "ip": "192.168.1.1"})
# {"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "message": "User login", "user_id": 123, "ip": "192.168.1.1"}
```

**Guarantees**:

- Single-line JSON (tracebacks compacted)
- Consistent schema across services
- Automatic correlation fields when ddtrace is active
- No ANSI codes or formatting artifacts

## 3. Scoped Debugging

Increase verbosity temporarily without changing configuration:

```python
from logspark import LogOverride
import logging

# Context manager
with LogOverride(level=logging.DEBUG):
    spark_logger.debug("Visible only in this scope")
    complex_operation()

# Decorator  
@LogOverride(level=logging.DEBUG)
def debug_function():
    spark_logger.debug("Debug inside this function")
```

**Properties**:

- Automatic restoration when scope ends
- No configuration mutation
- Thread-safe

## 4. Handler-Only Usage (No Singleton)

Use LogSpark handlers with existing loggers:

```python
import logging
from logspark.Handlers import TerminalHandler

# Works with any stdlib logger
logger = logging.getLogger("myapp")
logger.addHandler(TerminalHandler(show_time=True, show_path=False))
logger.setLevel(logging.INFO)

logger.info("Hello from stdlib logging")
```

**Benefits**:

- No singleton coupling
- Incremental adoption
- Rich formatting with existing code

## 5. Global Logger Control

Manage third-party logger behavior without code changes:

```python
from logspark import spark_log_manager

# Adopt existing loggers (snapshot-based)
spark_log_manager.adopt_all()

# Apply consistent formatting
spark_log_manager.unify(use_spark_handler=True)

# Or apply custom configuration
spark_log_manager.unify(
    level=logging.WARNING,  # Suppress noisy dependencies
    handler=JSONHandler(),
    propagate=False
)

# Release when done (doesn't revert mutations)
spark_log_manager.release_all()
```

**Use cases**:

- Suppress verbose third-party libraries
- Enforce consistent formatting across dependencies
- Incident response without redeployment

## Environment Configuration

Control behavior via environment variables:

```bash
# Performance optimization for CI/testing
export LOGSPARK_MODE=fast

# Correctness testing without output
export LOGSPARK_MODE=silenced

# Force Rich formatting (override terminal detection)
export FORCE_RICH=true
```

## Installation Options

```bash
# Basic installation
pip install logspark

# With optional features
pip install logspark[json]    # JSON structured logging
pip install logspark[color]   # Rich terminal colors
pip install logspark[trace]   # DDTrace integration
pip install logspark[all]     # Everything
```

## Next Steps

- **[Development Workflows](development-workflows.md)** - Local development and debugging patterns
- **[Production Observability](production-observability.md)** - Monitoring and log aggregation
- **[Incremental Adoption](incremental-adoption.md)** - Add LogSpark to existing projects
- **[Design Overview](design-overview.md)** - Why LogSpark works this way