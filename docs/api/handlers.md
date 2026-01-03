# Handlers

## TerminalHandler

::: logspark.Handlers.TerminalHandler

### Invariants

- **stdout by default** unless silenced or an explicit stream is provided
- **pre-config fallback uses stderr** when spark_logger is used before configure()
- **Rich rendering is delegated, not reimplemented**

## SparkJSONHandler

::: logspark.Handlers.SparkJSONHandler

### Guarantees

**Newlines and carriage returns are always normalized.**