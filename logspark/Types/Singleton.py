from .._Internal.State.SingletonClass import SingletonMeta


def is_singleton(instance: object) -> bool:
    """Return ``True`` if *instance* was created by a class using ``SingletonMeta``.

    Use this to distinguish between a raw ``SparkLogger`` (plain class, no
    singleton enforcement) and the pre-built singleton from ``logspark.Instance``
    (``_SparkLoggerInstance``, backed by ``SingletonMeta``).

    Example::

        from logspark.Types import is_singleton
        from logspark.Core import SparkLogger
        from logspark.Instance import spark_logger

        is_singleton(spark_logger)      # True
        is_singleton(SparkLogger())     # False

    """
    return isinstance(type(instance), SingletonMeta)


