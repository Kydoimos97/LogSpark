# Logging Policy

LogSpark treats logging behavior as **policy decisions** that affect your entire system's performance, storage costs, and operational predictability.

## Environment-Driven Behavior

LogSpark behavior adapts to deployment context via environment variables:

```bash
# Production: full accuracy and context
# (default behavior, no environment variable needed)

# CI/Testing: optimize for speed over accuracy  
export LOGSPARK_MODE=fast

# Performance testing: preserve semantics, discard output
export LOGSPARK_MODE=silenced

# Force Rich formatting (override terminal detection)
export FORCE_COLOR=true
```

## Performance Modes: Different Problems, Different Solutions

**Fast mode** and **silenced mode** solve different problems and must not be confused:

### Fast Mode (`LOGSPARK_MODE=fast`)

**Problem**: Frame walking is expensive in deep stacks (pytest + mocking + middleware)

**Solution**: Use pre-calibrated constant stacklevel instead of runtime frame inspection

**Tradeoffs**:

- **Pros**: Constant-time performance regardless of stack depth
- **Pros**: Eliminates frame walking overhead in CI
- **Cons**: Less accurate call-site attribution in unusual stack configurations
- **Cons**: Can hide realistic logging overhead during profiling

**When to use**: CI environments, deep test stacks, high-throughput scenarios where logging performance matters more than perfect call-site accuracy

### Silenced Mode (`LOGSPARK_MODE=silenced`)

**Problem**: Need to test logging correctness without output spam

**Solution**: Preserve full logging semantics but discard output without processing

**Tradeoffs**:

- **Pros**: Full logging pipeline exercised (formatting, filtering, record creation)
- **Pros**: Realistic performance characteristics for benchmarking
- **Pros**: No output clutter during testing
- **Cons**: Still incurs formatting and processing overhead

**When to use**: Correctness testing, performance benchmarking where you need realistic logging cost, test suites where output is noise

## Traceback Policy as System-Wide Decision

Exception verbosity is a global tradeoff affecting performance, storage, and debugging capability:

```python
from logspark.Types import TracebackOptions

# Maximum performance, minimal context
spark_logger.configure(traceback=TracebackOptions.NONE)

# Balanced performance and debugging (default)
spark_logger.configure(traceback=TracebackOptions.COMPACT)  

# Full debugging context, highest cost
spark_logger.configure(traceback=TracebackOptions.FULL)
```

**NONE**: Zero traceback overhead, fastest processing, requires external debugging tools

**COMPACT**: Single frame + exception info, moderate cost, sufficient for most debugging

**FULL**: Complete call stack, highest storage and processing cost, essential for complex debugging

This is **not a per-call decision**. Inconsistent traceback policies create:
- Unpredictable performance characteristics
- Operational confusion during incidents  
- Storage cost surprises
- Alert noise from verbose exceptions

## Performance as Operational Risk

In deep stacks, logging overhead can dominate runtime:

**Frame walking cost scales with call depth**: Each log record requires stack inspection. In test suites with extensive mocking or deep dependency chains, this compounds quickly.

**CI environments often discard output anyway**: Paying for call-site accuracy when logs are swallowed wastes compute resources and extends build times.

**Example scenario**:
```python
# Deep pytest stack with multiple fixtures and mocks
def test_complex_workflow():
    # 50+ frames deep when logging occurs
    # Frame walking happens on every log call
    # Multiplied by hundreds of log calls in test suite
    service.process_data()  # Logs internally
```

Fast mode eliminates this overhead at the cost of some call-site accuracy.

## Environment Detection and Overrides

LogSpark automatically detects environment capabilities:

**Terminal detection**:

- Checks terminal size (0x0 = unsupported)
- Detects SSH sessions and limited terminals
- Gracefully falls back to plain text

**Rich availability**:

- Imports Rich dynamically (fails gracefully if unavailable)
- Uses Rich Console for enhanced output when possible
- Falls back to stdlib StreamHandler when Rich unavailable

**Override mechanisms**:
```bash
# Force Rich even in detected incompatible terminals
export FORCE_COLOR=true

# Disable Rich entirely (testing fallback behavior)
unset FORCE_COLOR
```

## Policy Consistency Across Services

LogSpark enforces consistent policy decisions:

**Configuration immutability**: Once configured, behavior doesn't drift due to module load order or runtime mutations

**Global environment control**: Same environment variables affect all LogSpark instances consistently

**Traceback policy inheritance**: All handlers respect the same traceback policy, preventing mixed verbosity

**Performance mode uniformity**: Fast/silenced modes apply system-wide, not per-logger

This prevents operational surprises where different services have different logging behavior in the same environment.

## Decision Framework

When choosing logging policy:

1. **Development**: Default behavior (accurate call-sites, Rich formatting, COMPACT tracebacks)

2. **CI/Testing**: Fast mode if logging overhead is significant, silenced mode for correctness testing

3. **Production**: JSON preset with appropriate traceback policy for your storage/debugging balance

4. **Performance testing**: Silenced mode to measure realistic logging cost without output

5. **Incident response**: Temporarily switch to FULL tracebacks and DEBUG level via LogManager

The key insight: **logging policy affects system behavior**. Make it explicit and consistent.