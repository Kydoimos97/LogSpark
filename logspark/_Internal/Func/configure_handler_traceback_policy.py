import logging

from ...Types import TracebackOptions


def configure_handler_traceback_policy(handler: logging.Handler, policy: TracebackOptions) -> None:
    """
    Configure handler to include traceback policy in log records

    Args:
        handler: Handlers to configure
        policy: Traceback policy to apply
    """

    # Add a filter that injects traceback policy into log records
    class TracebackPolicyFilter(logging.Filter):
        def __init__(self, traceback_policy: TracebackOptions):
            super().__init__()
            self.traceback_policy = traceback_policy

        def filter(self, record: logging.LogRecord) -> bool:
            record.traceback_policy = self.traceback_policy
            return True

    handler.addFilter(TracebackPolicyFilter(policy))
