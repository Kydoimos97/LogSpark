"""Pre-built singleton instances of SparkLogger and SparkLogManager.

Import from here when you want the library-managed singletons::

    from logspark.Instance import spark_logger, spark_log_manager

Both instances are backed by ``SingletonMeta``: every call to
``_SparkLoggerInstance()`` or ``_SparkLogManagerInstance()`` returns the same
object. Use ``from logspark.Core import SparkLogger`` to create independent
instances without singleton semantics.
"""
from .._Internal.State import SingletonMeta
from ..Core import SparkLogger, SparkLogManager


class _SparkLoggerInstance(SparkLogger, metaclass=SingletonMeta):
    def __init__(self):
        super().__init__()


class _SparkLogManagerInstance(SparkLogManager, metaclass=SingletonMeta):
    def __init__(self):
        super().__init__()


spark_logger: SparkLogger = _SparkLoggerInstance()
spark_log_manager: SparkLogManager = _SparkLogManagerInstance()

__all__ = ["spark_logger", "spark_log_manager"]
