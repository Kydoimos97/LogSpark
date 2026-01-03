# Types API Reference

## Enum: TracebackOptions

Traceback inclusion policies for log output.

### Values

- `NONE` (None): No traceback information included
- `COMPACT` ("compact"): Single frame traceback (last frame only)  
- `FULL` ("full"): Complete traceback with all frames

### String Equivalents

TracebackOptions accepts both enum values and string equivalents:
```python
# These are equivalent
traceback=TracebackOptions.COMPACT
traceback="compact"

# Case insensitive
traceback="COMPACT"
traceback="Compact"
```

## Enum: PresetOptions

Predefined handler configurations.

### Values

- `TERMINAL` ("terminal"): TerminalHandler with Rich formatting when available
- `JSON` ("json"): SparkJSONHandler for structured output

### String Equivalents

PresetOptions accepts both enum values and string equivalents:
```python
# These are equivalent  
preset=PresetOptions.TERMINAL
preset="terminal"

# Case insensitive
preset="TERMINAL"
preset="Terminal"
```

## Exceptions

### FrozenConfigurationError

Raised when attempting to modify frozen logger configuration.

**Inheritance:** `LogSparkError` → `Exception`

### InvalidConfigurationError

Raised when configuration parameters are invalid.

**Inheritance:** `LogSparkError` → `Exception`

### UnfrozenGlobalOperationError

Raised when attempting global operations on unfrozen logger.

**Inheritance:** `LogSparkError` → `Exception`

### MissingDependencyException

Raised when required optional dependencies are unavailable.

**Inheritance:** `LogSparkError` → `Exception`

**Constructor:**
```python
MissingDependencyException(dependencies: list[str])
```

## Warnings

### UnconfiguredUsageWarning

Warning emitted when using logger before configuration.

**Inheritance:** `UserWarning`

### IncompatibleConsoleWarning

Warning emitted when Rich is available but terminal is not compatible.

**Inheritance:** `UserWarning`

## Protocols

### SupportsWrite

Protocol for objects that support write operations (streams).

```python
def write(self, s: str) -> int | None: ...
```