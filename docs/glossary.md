# Glossary

Reference definitions for LogSpark components and terms. Use this page for lookups, not sequential reading.

---

## Logger

The configuration owner and lifecycle anchor for the entire logging pipeline. The logger holds the handler list, applies level filtering, and in LogSpark enforces that configuration happens exactly once via [`configure()`](lifecycle.md#configure).

A logger is what you call `.info()`, `.debug()`, `.exception()` etc. on, but its more important role is owning the pipeline setup. When you call `logger.configure()`, you are setting up handlers, filters, and formatters in one shot.

**LogSpark specifics:**

- `SparkLogger` is a singleton: one instance per process
- Once `configure()` is called the logger is [frozen](glossary.md#freeze) and cannot be mutated
- Logging before `configure()` is allowed but emits a [`SparkLoggerUnconfiguredUsageWarning`](reference.md#exceptions)

See [Lifecycle](lifecycle.md).

---

## Handler

Routes a log record to a destination. Each handler owns exactly one formatter and delivers records to one output target: a terminal, a file, a network endpoint.

Handlers are stdlib-compatible and can be attached to any `logging.Logger`, not just the LogSpark singleton.

| Handler | Output | When to use |
|---|---|---|
| [`SparkTerminalHandler`](reference.md#terminalhandler) | stdout | Development, interactive use |
| [`SparkJsonHandler`](reference.md#jsonhandler) | stdout (JSON) | Production, log aggregation |
| [`SparkRichHandler`](reference.md#richhandler) | stdout (Rich) | Development with `rich` installed |
| `SparkPreConfigHandler` | stdout | Internal: used before `configure()` is called, not for direct use |

---

## Filter

A pipeline step that reads and writes the log record before it reaches a handler. In LogSpark, filters are primarily enrichment: they attach structured data to the record so downstream handlers and formatters have more to work with. Gating (actually excluding records) is the secondary use case.

Filters run on the logger, in order, before any handler receives the record.

| Filter | What it attaches |
|---|---|
| [`PathNormalizationFilter`](reference.md#pathnormalizationfilter) | Normalized file path, line number, OSC 8 hyperlink URI |
| [`TracebackPolicyFilter`](reference.md#tracebackpolicyfilter) | Exception type, value, traceback structured for formatter use |
| [`DDTraceInjectionFilter`](reference.md#ddtraceinjectionfilter) | Datadog `dd_trace_id` and `dd_span_id` when ddtrace is active |

Order matters if one filter reads data written by another.

---

## Formatter

Renders the final string written to the handler's destination. The formatter is the last stage in the pipeline and has access to everything on the record, including anything filters attached.

A formatter is always owned by a handler, not the logger. Different destinations need different formatters.

| Formatter | Use |
|---|---|
| [`SparkBaseFormatter`](reference.md#sparkbaseformatter) | Plain text with traceback policy enforcement |
| [`SparkColorFormatter`](reference.md#sparkcolorformatter) | ANSI color-coded terminal output |
| [`SparkJsonFormatter`](reference.md#sparkjsonformatter) | Single-line JSON with traceback flattening |

---

## Log Record

The object that travels through the pipeline. Created when you call `.info()`, `.error()` etc. Contains the message, level, timestamp, file path, line number, and exception info if present.

Filters in LogSpark attach additional data via a `record.spark` attribute (`SparkRecordAttrs`) carrying normalized path info and structured exception data.

---

## Freeze

The state a logger enters after `configure()` completes. A frozen logger cannot have handlers added, filters added, or `configure()` called again. Any attempt raises [`FrozenClassException`](reference.md#exceptions).

Freeze exists to prevent configuration drift. Once the logger is set up, nothing can silently change it.

See [Lifecycle: Freeze](lifecycle.md#freeze).

---

## TempLogLevel

A context manager and decorator that temporarily changes the logger's effective level for a block or function. Does not affect the frozen configuration: handlers and filters are unchanged.

```python
with TempLogLevel(logging.DEBUG):
    logger.debug("visible here")
```

See [Temporary Log Level](tmp_log.md).

---

## SparkLogManager

A utility for batch-mutating existing `logging.Logger` instances, typically third-party library loggers. Snapshot-based: only loggers that exist at the time of `adopt_all()` are managed. Does not restore previous state when loggers are released.

See [SparkLogManager](log_management.md).

---

## TracebackOptions

Controls how exceptions are rendered in log output. Passed to [`configure()`](lifecycle.md#configure) or directly to a handler.

| Value | Output |
|---|---|
| `COMPACT` | Exception type, message, and single frame location. Default. |
| `FULL` | Full traceback with all frames |
| `HIDE` | Exception type and message only |

See [Output Modes: Traceback policy](output-modes.md#traceback-policy).

---

## PathResolutionSetting

Controls how file paths appear in log lines. Passed to [`configure()`](lifecycle.md#configure).

| Value | Output |
|---|---|
| `RELATIVE` | Relative to project root, e.g. `src/server.py:14`. Default. |
| `ABSOLUTE` | Full absolute path |
| `FILE` | Filename only, e.g. `server.py:14` |

See [Output Modes: Path resolution](output-modes.md#path-resolution).

---

## LOGSPARK_MODE

Environment variable controlling the logger's operational profile.

| Value | Effect |
|---|---|
| *(unset)* | Default behavior |
| `fast` | Constant-time stacklevel resolution, reduced call-site accuracy |
| `silenced` | Full pipeline active, output discarded |

See [Environment Variables](environment.md#logspark_mode).
