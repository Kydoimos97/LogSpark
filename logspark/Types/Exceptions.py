class LogSparkError(Exception):
    """Base exception for LogSpark logging errors"""

    pass


class FrozenClassException(LogSparkError):
    """Raised when attempting to modify frozen configuration"""

    pass


class UnfrozenGlobalOperationError(LogSparkError):
    """Raised when attempting to do an operation that requires a frozen state"""

    pass


class InvalidConfigurationError(LogSparkError):
    """Raised when configuration parameters are invalid"""

    pass

class LogSparkWarning(Warning):
    """Base warning for LogSpark logging warnings"""



class SparkLoggerUnconfiguredUsageWarning(LogSparkWarning):
    """Warning for logging before explicit configuration"""

    pass

class SparkLoggerDuplicatedElementWarning(LogSparkWarning):
    """Base warning for duplicated handlers or filters attached to the logger."""

class SparkLoggerDuplicatedHandlerWarning(SparkLoggerDuplicatedElementWarning):
    """Warning for duplicated handlers"""

    pass

class SparkLoggerDuplicatedFilterWarning(SparkLoggerDuplicatedElementWarning):
    """Warning for duplicated filters"""
    pass


class MissingDependencyException(LogSparkError):
    """Raised when a required optional dependency is not installed."""

    def __init__(self, dependencies: list[str]) -> None:
        msg = f"Missing required dependencies:\n{', '.join(dependencies)}\n"
        super().__init__(msg)
