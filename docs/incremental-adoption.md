# Incremental Adoption

LogSpark components work independently, enabling gradual adoption without forced migration. Start with any piece that solves your immediate problem.

## The Adoption Spectrum

LogSpark supports multiple adoption paths:

1. **Handlers only** - Better output with existing loggers
2. **Filters only** - Add correlation data to existing infrastructure  
3. **Logger adoption** - Centralized configuration and identity
4. **Global control** - Operational management of third-party loggers

Each provides value independently. Choose what fits your current needs.

## Path 1: Handlers Without Singleton

Use LogSpark handlers with your existing logging setup:

```python
import logging
from logspark.Handlers import TerminalHandler, SparkJSONHandler

# Development setup
dev_logger = logging.getLogger("myapp")
dev_logger.addHandler(TerminalHandler(show_time=True, show_path=False))
dev_logger.setLevel(logging.INFO)

# Production setup  
prod_logger = logging.getLogger("myapp")
prod_logger.addHandler(SparkJSONHandler())
prod_logger.setLevel(logging.WARNING)
```

**Benefits**:

- Rich terminal formatting when available
- Structured JSON output for production
- No singleton coupling or configuration freeze
- Works with existing logging patterns

**When to use**: You like your current logging setup but want better output formatting.

## Path 2: Correlation Filters Only

Add distributed tracing to existing handlers:

```python
from logspark.Filters import DDTraceCorrelationFilter

# Add to any existing handler
existing_handler = logging.StreamHandler()
existing_handler.addFilter(DDTraceCorrelationFilter())

logger = logging.getLogger("myapp")
logger.addHandler(existing_handler)

# Logs now include dd_trace_id and dd_span_id when ddtrace is active
logger.info("Processing request", extra={"user_id": 123})
```

**Benefits**:

- Automatic correlation data injection
- No handler or logger changes needed
- Works with any logging infrastructure
- Fails gracefully when ddtrace unavailable

**When to use**: You need distributed tracing correlation but don't want to change logging infrastructure.

## Path 3: Gradual Logger Migration

Migrate from handlers to centralized logger configuration:

```python
# Phase 1: Start with handlers
from logspark.Handlers import TerminalHandler
logger = logging.getLogger("myapp")
logger.addHandler(TerminalHandler())

# Phase 2: Move to LogSpark logger for consistency
from logspark import spark_logger
spark_logger.configure(level=logging.INFO, preset="terminal")

# Phase 3: Replace direct logger usage
# Old: logger.info("message")
# New: spark_logger.info("message")
```

**Benefits**:

- Immutable configuration prevents drift
- Stable identity in deep stacks
- Consistent behavior across modules
- Scoped debugging with LogOverride

**When to use**: You want configuration discipline and stable logger identity.

## Path 4: Global Control When Ready

Add operational control over third-party loggers:

```python
from logspark import spark_log_manager

# Adopt existing loggers for management
spark_log_manager.adopt_all()

# Apply consistent policy
spark_log_manager.unify(
    level=logging.WARNING,  # Suppress noisy dependencies
    use_spark_handler=True  # Consistent formatting
)

# Release when operational need ends
spark_log_manager.release_all()
```

**Benefits**:

- Suppress verbose third-party libraries
- Enforce consistent formatting across dependencies
- Rapid incident response capabilities
- No code changes in managed libraries

**When to use**: You need operational control over logging behavior across multiple libraries.

## Mixed Adoption Strategies

Combine approaches based on different needs:

```python
# Core application: Use LogSpark logger
from logspark import spark_logger
spark_logger.configure(level=logging.INFO, preset="json")

# Legacy module: Use handler only
legacy_logger = logging.getLogger("legacy")
legacy_logger.addHandler(SparkJSONHandler())

# Third-party noise: Use global control
from logspark import spark_log_manager
spark_log_manager.adopt(logging.getLogger("urllib3"))
spark_log_manager.unify(level=logging.ERROR)
```

Each component solves different problems without interfering with others.

## Migration Safety

LogSpark's design prevents adoption risks:

**No breaking changes**: All components use standard logging interfaces. Existing code continues working.

**No forced dependencies**: Handlers work without the logger. Logger works without global control. Each piece is optional.

**No configuration conflicts**: LogSpark doesn't mutate global logging state unless explicitly requested via LogManager.

**Gradual rollback**: Remove any component without affecting others. No all-or-nothing commitment.