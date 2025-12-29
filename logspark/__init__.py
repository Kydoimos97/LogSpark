# Create singleton instances
from .SparkLoggerDef import spark_logger, SparkLogger
from .SparkLogManagerDef import spark_log_manager, SparkLogManager
from .LogOverrideDef import LogOverride
from . import Types, Handlers

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
