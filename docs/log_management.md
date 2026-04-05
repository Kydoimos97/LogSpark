# SparkLogManager

Third-party libraries bring their own loggers. Some are noisy. Some attach handlers that conflict with yours. `SparkLogManager` gives you explicit, batch control over those loggers without touching their source code.

## What it is

A snapshot-based utility for mutating existing `logging.Logger` instances. It does not own or proxy those loggers, does not intercept their log calls, and does not restore previous state when you release them. It snapshots at a point in time: loggers created after adoption are not affected.

## Adopting loggers

Adopt all currently registered loggers:

```python
from logspark import spark_log_manager

spark_log_manager.adopt_all()
```

Adopt a specific logger:

```python
import logging
from logspark import spark_log_manager

spark_log_manager.adopt(logging.getLogger("httpx"))
```

`adopt_all()` excludes `LogSpark` itself by default. Pass `ignore=["name"]` to exclude additional loggers.

**Important:** call `adopt_all()` after importing your dependencies, not before. Loggers that have not yet been created cannot be adopted.

## Applying changes with unify()

`unify()` applies configuration to all managed loggers at once:

```python
import logging
from logspark import spark_log_manager

spark_log_manager.adopt_all()
spark_log_manager.unify(level=logging.WARNING, propagate=False)
```

Copy LogSpark's own handler and filters to all managed loggers, the canonical way to unify all output through your handler:

```python
from logspark import logger, spark_log_manager

logger.configure()  # must be frozen first

spark_log_manager.adopt_all()
spark_log_manager.unify(copy_spark_logger_config=True, propagate=False)
```

`unify()` parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | `int \| str \| None` | `None` | Level to apply to all managed loggers. `None` leaves existing levels unchanged. |
| `handlers` | `list[logging.Handler] \| None` | `None` | Replaces existing handlers on all managed loggers. |
| `filters` | `list[logging.Filter] \| None` | `None` | Replaces existing filters on all managed loggers. |
| `propagate` | `bool \| None` | `None` | Sets propagation on all managed loggers. `None` leaves unchanged. |
| `copy_spark_logger_config` | `bool` | `False` | Copies handlers and filters from the frozen `spark_logger`. Requires LogSpark to be configured and frozen. |

`unify()` is destructive: existing handlers are cleared when `handlers` or `copy_spark_logger_config` is used. Previous state is not preserved.

## Inspecting managed loggers

```python
print(spark_log_manager.managed_names)
# ['httpx', 'sqlalchemy', 'urllib3', ...]

httpx_logger = spark_log_manager.managed("httpx")
```

## Releasing loggers

Release removes a logger from management. It does not undo mutations applied by `unify()`.

```python
spark_log_manager.release("httpx")
spark_log_manager.release_all()
```

## Common patterns

Silence a noisy library:

```python
import logging
from logspark import spark_log_manager

spark_log_manager.adopt(logging.getLogger("sqlalchemy.engine"))
spark_log_manager.unify(level=logging.WARNING)
```

Unify all output through LogSpark's handler:

```python
import logging
import httpx       # import dependencies first so their loggers are registered
import sqlalchemy

from logspark import logger, spark_log_manager

logger.configure()

spark_log_manager.adopt_all()
spark_log_manager.unify(
    copy_spark_logger_config=True,
    level=logging.INFO,
    propagate=False,
)
```
