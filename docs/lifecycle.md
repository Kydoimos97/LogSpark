# Lifecycle

LogSpark enforces a strict lifecycle for the logger:

```
configure() -> freeze -> use
```

This is the most important thing to understand about LogSpark. Everything else follows from it.

---

## Why a lifecycle?

Stdlib logging has no lifecycle. You can call `addHandler()` at any point, reconfigure at any point, and nothing stops you. In a real application this means configuration state becomes unpredictable. A module imported late can silently change how the root logger behaves.

LogSpark treats logging as infrastructure. Infrastructure is configured once at startup, then used. It does not reconfigure at runtime.

---

## configure()

`configure()` is the single entry point for setting up the logger. Call it once, early, before threads or workers start.

```python
import logging
from logspark import logger
from logspark.Types.Options import TracebackOptions, PathResolutionSetting

logger.configure(
    level=logging.INFO,
    traceback_policy=TracebackOptions.COMPACT,
    path_resolution=PathResolutionSetting.RELATIVE,
    multiline=True,
)
```

What `configure()` does:

1. Validates the level
2. Creates the appropriate handler if none is provided
3. Attaches configured filters
4. Freezes the logger (unless `no_freeze=True`)

After `configure()` returns, the logger is [frozen](glossary.md#freeze). No further calls to `addHandler()`, `addFilter()`, `eject_handlers()`, or `configure()` will succeed. They raise [`FrozenClassException`](reference.md#exceptions).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | `str \| int` | `logging.INFO` | Minimum log level |
| `handler` | `logging.Handler` | `None` | Custom handler. If omitted, LogSpark creates a `SparkTerminalHandler`. |
| `traceback_policy` | [`TracebackOptions`](glossary.md#tracebackoptions) | `COMPACT` | How exceptions are rendered |
| `path_resolution` | [`PathResolutionSetting`](glossary.md#pathresolutionsetting) | `RELATIVE` | How file paths appear in log lines |
| `multiline` | `bool` | `True` | Whether log output can span multiple lines |
| `no_freeze` | `bool` | `False` | Skip automatic freeze after configure. Advanced use only. |

---

## Freeze

Once frozen, the logger is immutable for the lifetime of the process:

- Handler list is locked
- Filter list is locked
- `configure()` cannot be called again
- `addHandler()`, `addFilter()`, and `eject_handlers()` raise [`FrozenClassException`](reference.md#exceptions) immediately

By default, `configure()` freezes automatically. Deferring with `no_freeze=True` and calling `logger.freeze()` manually is only needed in unusual initialization sequences:

```python
logger.configure(level="DEBUG", no_freeze=True)
# ... additional setup
logger.freeze()
```

### Checking state

```python
logger.is_configured  # True after configure()
logger.frozen         # True after freeze
```

---

## Before configure() is called

Logging before `configure()` does not silently discard records. LogSpark:

1. Emits a [`SparkLoggerUnconfiguredUsageWarning`](reference.md#exceptions) once per process
2. Falls back to a minimal `SparkPreConfigHandler` with a simple stdout format

Logging never disappears, but lifecycle violations are always surfaced.

---

## kill() -- resetting the singleton

`kill()` forcefully resets the logger singleton. It exists for test isolation only.

```python
logger.kill()
# logger is now uninitialized -- next call creates a fresh instance
```

Do not use `kill()` in application code. It bypasses all lifecycle guarantees.

---

## TempLogLevel -- scoped level overrides

If you need debug output from a specific path without reconfiguring, use [`TempLogLevel`](advanced.md#scoped-log-level-overrides--temploglevel). It bypasses freeze only for the effective level. Handlers and filters are untouched.
