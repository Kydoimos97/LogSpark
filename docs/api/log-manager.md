# LogManager

::: logspark.SparkLogManagerDef.SparkLogManager

## Implementation Notes

**Handler Sharing**: `use_spark_handler=True` copies the handler object, not a clone.

**Adoption Scope**: Loggers created after `adopt_all()` are not managed.

## Global Instance

::: logspark.spark_log_manager