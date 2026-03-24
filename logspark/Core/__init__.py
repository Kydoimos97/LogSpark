from .SparkLogger import SparkLogger
from .SparkLogManager import SparkLogManager
from .TempLogLevel import TempLogLevel

# Singleton Patterns
spark_log_manager = SparkLogManager()
spark_logger = SparkLogger()

__all__ = ["spark_log_manager", "spark_logger",
           "TempLogLevel"]

