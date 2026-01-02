# Global Log Control

The LogManager enables operational control over third-party logger behavior without code changes. Use it for incident response, dependency noise suppression, and consistency enforcement.

## The Operational Problem

Third-party libraries create logging chaos in production:

```python
# Your clean application logging
spark_logger.info("Processing order", extra={"order_id": "123"})

# Noisy dependency logging (you can't control)
# urllib3: "Starting new HTTPS connection (1): api.example.com:443"
# boto3: "Found credentials in environment variables"  
# requests: "Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None))"
```

This creates:

- **Alert fatigue** from verbose dependency logs triggering monitoring rules
- **Inconsistent formatting** breaking log aggregation pipelines
- **Missing correlation data** for distributed tracing
- **Storage cost** from high-volume debug logs in production

LogManager solves this through **snapshot-based adoption** and **batch mutation**.

## Adopt, Unify, Release Pattern

**Step 1: Adopt existing loggers (snapshot-based)**
```python
from logspark import spark_log_manager

# Snapshot all current loggers
spark_log_manager.adopt_all()

# Or adopt specific problematic loggers
spark_log_manager.adopt(logging.getLogger("urllib3"))
spark_log_manager.adopt(logging.getLogger("boto3"))
```

**Step 2: Apply consistent policy**
```python
# Use LogSpark's handler for consistent formatting
spark_log_manager.unify(use_spark_handler=True)

# Or apply custom configuration
spark_log_manager.unify(
    level=logging.WARNING,  # Suppress INFO/DEBUG noise
    handler=JSONHandler(),  # Consistent JSON output
    propagate=False         # Prevent duplicate logs
)
```

**Step 3: Release when done**
```python
# Release specific logger
spark_log_manager.release("urllib3")

# Release all managed loggers  
spark_log_manager.release_all()
```

**Important**: Release clears management but **does not revert mutations**. The loggers keep their modified configuration.

## Real-World Scenarios

### Dependency Noise Suppression

```python
# Before: Noisy logs from multiple sources
# urllib3.connectionpool: Starting new HTTPS connection
# boto3.session: Loading credentials from environment  
# requests.adapters: Retrying connection

spark_log_manager.adopt_all()
spark_log_manager.unify(
    level=logging.ERROR,    # Only errors from dependencies
    use_spark_handler=True  # JSON format for consistency
)

# After: Clean production logs with only errors
```

### Correlation Data Injection

```python
# Add correlation filters to all managed loggers
from logspark.Filters import DDTraceCorrelationFilter

spark_log_manager.adopt_all()
spark_log_manager.unify(use_spark_handler=True)

# All managed loggers now include trace correlation
# No code changes needed in dependencies
```

## Snapshot-Based Adoption

**Key insight**: LogManager only manages loggers that exist **at adoption time**.

```python
import logging

# Create some loggers
logger_a = logging.getLogger("service_a")
logger_b = logging.getLogger("service_b")

# Adopt current loggers
spark_log_manager.adopt_all()  # Manages: service_a, service_b

# Create new logger after adoption
logger_c = logging.getLogger("service_c")  # NOT managed

# To manage new loggers, adopt again
spark_log_manager.adopt(logger_c)  # Now managed
```

This prevents unintended side effects on loggers created by code you don't control.

## Operational Safety Guarantees

**No ownership transfer**: LogManager mutates existing loggers using stdlib mechanisms. Your code continues working unchanged.

**Explicit scope**: Only adopted loggers are affected. No automatic capture of all logging in the process.

**Batch operations**: Changes apply to all managed loggers simultaneously, ensuring consistency.

**Release safety**: Releasing management doesn't break logging - loggers continue with their current configuration.

## When to Use Global Control

**Use LogManager when**:

- Third-party libraries generate excessive logging noise
- You need consistent formatting across multiple loggers
- Incident response requires rapid verbosity changes
- Distributed tracing needs correlation data injection

**Don't use LogManager when**:

- You have simple applications with single loggers
- You need fine-grained per-logger control
- You want to avoid any global state management

## Management Inspection

Monitor what LogManager is controlling:

```python
# See which loggers are managed
managed_names = spark_log_manager.managed_names
print(f"Managing {len(managed_names)} loggers: {managed_names}")

# Access specific managed logger
if "urllib3" in managed_names:
    urllib3_logger = spark_log_manager.managed("urllib3")
    print(f"urllib3 level: {urllib3_logger.level}")
```

This visibility helps during debugging and operational changes.