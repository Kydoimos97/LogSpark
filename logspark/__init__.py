from .Core import log_override, spark_log_manager, spark_logger

logger = spark_logger

__all__ = ["logger", "spark_logger", "spark_log_manager", "log_override"]
