# Create singleton instances
from . import Handlers, Types
from .LogOverrideDef import LogOverride
from .SparkLoggerDef import SparkLogger, spark_logger
from .SparkLogManagerDef import SparkLogManager, spark_log_manager

logger = spark_logger

__all__ = [
    "logger",
    "spark_logger",
    "spark_log_manager",
    "SparkLogger",
    "SparkLogManager",
    "LogOverride",
    "Types",
    "Handlers",
]
