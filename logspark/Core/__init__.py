from .LogOverride import LogOverride
from .SparkLogger import SparkLogger
from .SparkLogManager import SparkLogManager

# Singleton Patterns
spark_log_manager = SparkLogManager()
spark_logger = SparkLogger()

# Aliases
log_override = LogOverride

__all__ = ["spark_log_manager", "spark_logger", "log_override"]
