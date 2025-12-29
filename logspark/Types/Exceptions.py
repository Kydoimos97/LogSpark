class LogSparkError(Exception):
    """Base exception for LogSpark logging errors"""

    pass


class FrozenConfigurationError(LogSparkError):
    """Raised when attempting to modify frozen configuration"""

    pass


class UnfrozenGlobalOperationError(LogSparkError):
    """Raised when attempting to do an operation that requires a frozen state"""

    pass


class InvalidConfigurationError(LogSparkError):
    """Raised when configuration parameters are invalid"""

    pass


class UnconfiguredUsageWarning(UserWarning):
    """Warning for logging before explicit configuration"""

    pass


class MissingDependencyException(LogSparkError):
    def __init__(self, dependencies: list[str]) -> None:
        msg = f"Missing required dependencies:\n{', '.join(dependencies)}\n"
        super().__init__(msg)


class IncompatibleConsoleWarning(UserWarning):
    """Warning emitted when found console is not compatible with rich"""

    pass
