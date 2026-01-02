# Development Experience

LogSpark optimizes for developer productivity through sane defaults, intelligent environment detection, and scoped debugging capabilities.

## Sane Defaults

The terminal preset provides human-friendly output optimized for development workflows:

- **Structured layout** with consistent field positioning
- **Syntax highlighting** for log levels and messages
- **Clickable file paths** for direct navigation to source
- **Function name display** for call-site identification
- **Configurable verbosity** for time, level, and path information

## Rich When Available

LogSpark detects Rich availability and terminal compatibility without configuration:

**Rich available + compatible terminal**: Full Rich formatting with colors, layout, and enhanced tracebacks

**Rich available + incompatible terminal**: Graceful fallback to stdlib StreamHandler with warning

**Rich unavailable**: Silent fallback to stdlib StreamHandler

## SSH and No-Color Terminals

LogSpark handles constrained terminal environments:

- **SSH sessions** with limited color support
- **CI/CD environments** with no terminal interaction
- **Redirected output** to files or pipes
- **Screen readers** and accessibility tools

Terminal compatibility detection prevents formatting artifacts and ensures readable output across all environments.

**Pre-configuration behavior:** When spark_logger is used before configure(), LogSpark emits via a minimal pre-config handler to stderr. This is intentional. Pre-config logging represents a diagnostic lifecycle state and must not pollute stdout, which may later be used for structured output (e.g. JSON pipelines). After configuration, handlers are stdout-oriented by default, unless explicitly overridden.

## Scoped Debugging via Overrides

LogOverride enables temporary verbosity increases without configuration changes:

```python
# Context manager for scoped debugging
with LogOverride(level=logging.DEBUG):
    complex_operation()  # Debug logs visible only in this scope

# Decorator for function-level debugging  
@LogOverride(level=logging.DEBUG)
def debug_function():
    pass  # Function runs with debug logging enabled
```

Overrides are:

- **Local**: Affect only the current scope
- **Fast**: No configuration mutation or global state changes
- **Reversible**: Automatically restore original level on exit

## Performance Considerations

Development mode prioritizes readability over performance:

- **Frame walking** for accurate call-site attribution
- **Rich rendering** for enhanced visual output  
- **Detailed tracebacks** for debugging context

Production deployments should use JSON preset for optimal performance and structured output.

## Environment Detection

LogSpark automatically adapts to development environments:

- **Interactive terminals**: Full Rich formatting
- **IDEs and editors**: Compatible output with clickable links
- **Jupyter notebooks**: Appropriate formatting for cell output
- **Testing frameworks**: Minimal overhead and clear output

No manual configuration required. The system detects and adapts to the runtime environment.