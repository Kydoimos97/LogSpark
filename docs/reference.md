# Component Reference

Full API reference for all LogSpark components. For conceptual background, see [Concepts](concepts.md) and the [Glossary](glossary.md).

---

## Handlers

Handlers route log records to a destination. Each handler owns its formatter. See [Glossary: Handler](glossary.md#handler).

---

### SparkTerminalHandler

Human-readable terminal output. Default handler when `configure()` is called without an explicit handler. Automatically upgrades to [`SparkRichHandler`](#richhandler) if `rich` is installed.

```python
from logspark.Handlers import SparkTerminalHandler
from logspark import logger

logger.configure(handler=SparkTerminalHandler(level="DEBUG", show_function=True))
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | `int \| str` | `NOTSET` | Minimum level for this handler |
| `stream` | `SupportsWrite` | `sys.stdout` | Output stream |
| `use_color` | `bool` | `True` | Enable ANSI color output if the terminal supports it |
| `show_time` | `bool` | `True` | Include timestamp |
| `show_level` | `bool` | `True` | Include level name |
| `show_path` | `bool` | `True` | Include file path and line number |
| `show_function` | `bool` | `False` | Include calling function name |
| `traceback_policy` | [`TracebackOptions`](glossary.md#tracebackoptions) | `None` | Traceback rendering policy |
| `multiline` | `bool` | `True` | Allow multiline output |
| `log_time_format` | `str` | `"%H:%M:%S"` | strftime format for timestamps |

---

### SparkJsonHandler

Single-line JSON output for production and log aggregation pipelines.

```python
from logspark.Handlers import SparkJsonHandler
from logspark import logger

logger.configure(handler=SparkJsonHandler())
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `stream` | `SupportsWrite` | `sys.stdout` | Output stream |

**Output invariants:**

- One JSON object per line, always
- No ANSI escape codes
- Exception tracebacks flattened to single-line strings before serialization
- `extra` fields appear as top-level JSON keys

**Requires:** `python-json-logger`

---

### SparkRichHandler

Rich-enhanced terminal output with structured column layout, clickable file paths, and improved exception rendering.

```python
from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
from logspark.Types.Options import SparkRichHandlerSettings
from logspark import logger

settings = SparkRichHandlerSettings(min_message_width=60, max_path_width=40)
logger.configure(handler=SparkRichHandler(show_function=True, settings=settings))
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | `int \| str` | `NOTSET` | Minimum level for this handler |
| `console` | `Console` | `None` | Pre-configured Rich Console. Mutually exclusive with `stream`. |
| `stream` | `SupportsWrite` | `None` | Output stream. Used to construct a Console internally. |
| `use_color` | `bool` | `True` | Enable color output |
| `traceback_policy` | [`TracebackOptions`](glossary.md#tracebackoptions) | `COMPACT` | Traceback rendering policy |
| `show_time` | `bool` | `True` | Include timestamp column |
| `show_level` | `bool` | `True` | Include level column |
| `show_path` | `bool` | `True` | Include path column |
| `show_function` | `bool` | `False` | Include function name column |
| `log_time_format` | `str` | `"%H:%M:%S"` | Timestamp format |
| `settings` | `SparkRichHandlerSettings` | `None` | Advanced layout settings (see below) |

**SparkRichHandlerSettings:**

| Field | Type | Default | Description |
|---|---|---|---|
| `min_message_width` | `int` | `40` | Minimum character width reserved for the message column |
| `max_path_width` | `int` | `40` | Maximum character width for the path column |
| `max_function_width` | `int` | `25` | Maximum character width for the function name column |
| `omit_repeated_times` | `bool` | `True` | Suppress duplicate timestamps on consecutive lines |
| `enable_link_path` | `bool` | `True` | Make file paths clickable in supporting terminals |
| `tracebacks_width` | `int \| None` | `None` | Override traceback panel width |
| `tracebacks_extra_lines` | `int` | `3` | Extra context lines around exception frames |
| `indent_guide` | `str \| None` | `"\|"` | Character used for multiline indent guides |

**Requires:** `rich`

---

## Filters

Filters enrich log records before they reach a handler, and optionally reject records. See [Glossary: Filter](glossary.md#filter).

Filters listed here are attached automatically by `configure()` when the relevant option is set. You only need to attach them manually when building a custom pipeline without using `configure()`.

---

### PathNormalizationFilter

Rewrites file path information on the log record according to the configured [`PathResolutionSetting`](glossary.md#pathresolutionsetting). Also attaches a `file://` URI for terminal link support.

Attached automatically when `configure()` is called with a `path_resolution` setting.

```python
from logspark.Filters import PathNormalizationFilter
from logspark.Types.Options import PathResolutionSetting

f = PathNormalizationFilter(resolution_mode=PathResolutionSetting.RELATIVE)
```

After this filter runs, the record carries `record.spark.filepath`, `record.spark.filename`, `record.spark.lineno`, and `record.spark.uri`.

---

### TracebackPolicyFilter

Marks log records that carry exception info so downstream formatters apply traceback policy correctly. Sets `record._spark_exc = True` and populates `record.spark` with structured exception data.

Attached automatically when `configure()` is called with a `traceback_policy` setting.

---

### DDTraceInjectionFilter

Injects Datadog trace correlation fields (`dd_trace_id`, `dd_span_id`) into log records when `ddtrace` is active and a span is running. Attached automatically when `ddtrace` is importable. No configuration required.

---

## Formatters

Formatters render the final string written to a destination. Owned by handlers, not the logger. See [Glossary: Formatter](glossary.md#formatter).

---

### SparkBaseFormatter

Base formatter with traceback policy support. Used as the fallback when color output is unavailable.

```python
from logspark.Formatters import SparkBaseFormatter
from logspark.Types.Options import TracebackOptions

fmt = SparkBaseFormatter(
    fmt="%(asctime)s %(levelname)s %(message)s",
    tb_policy=TracebackOptions.COMPACT,
    multiline=True,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fmt` | `str \| None` | `None` | stdlib format string |
| `datefmt` | `str \| None` | `None` | strftime date format |
| `tb_policy` | [`TracebackOptions`](glossary.md#tracebackoptions) | `None` | Traceback rendering policy |
| `multiline` | `bool` | `True` | Allow multiline output |

---

### SparkColorFormatter

Extends `SparkBaseFormatter` with ANSI color coding by log level. Used automatically by [`SparkTerminalHandler`](#terminalhandler) on color-compatible terminals.

---

### SparkJsonFormatter

Wraps `python-json-logger` to enforce the single-line JSON output invariant. Used by [`SparkJsonHandler`](#jsonhandler). Tracebacks are flattened to single-line strings before serialization.

---

## Options

### TracebackOptions

```python
from logspark.Types.Options import TracebackOptions
```

| Value | Description |
|---|---|
| `TracebackOptions.COMPACT` | Exception type, message, and single frame location. Default. |
| `TracebackOptions.FULL` | Full traceback with all frames |
| `TracebackOptions.HIDE` | Exception type and message only |

See [Output Modes: Traceback policy](output-modes.md#traceback-policy).

---

### PathResolutionSetting

```python
from logspark.Types.Options import PathResolutionSetting
```

| Value | Description |
|---|---|
| `PathResolutionSetting.RELATIVE` | Relative to project root. Default. |
| `PathResolutionSetting.ABSOLUTE` | Full absolute path |
| `PathResolutionSetting.FILE` | Filename only |

See [Output Modes: Path resolution](output-modes.md#path-resolution).

---

## Exceptions

| Exception | Raised when |
|---|---|
| `FrozenClassException` | Any mutation attempt on a frozen logger: `addHandler()`, `addFilter()`, `configure()`, `eject_handlers()`, etc. |
| `InvalidConfigurationError` | Configuration parameters are invalid or the logger has no handlers when `is_configured` is set |
| `UnfrozenGlobalOperationError` | An operation requires a frozen logger, e.g. `SparkLogManager.unify(copy_spark_logger_config=True)` before freeze |
| `MissingDependencyException` | A handler or formatter requires a package that is not installed (`rich`, `python-json-logger`) |
| `SparkLoggerUnconfiguredUsageWarning` | A log call was made before `configure()`. Emitted once per process. |
| `SparkLoggerDuplicatedHandlerWarning` | `addHandler()` was called with a handler type already present and `dedupe=False` |
| `SparkLoggerDuplicatedFilterWarning` | `addFilter()` was called with a filter type already present and `dedupe=False` |
