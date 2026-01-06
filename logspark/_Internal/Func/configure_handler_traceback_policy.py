import logging

from ...Types import TracebackOptions


def configure_handler_traceback_policy(handler: logging.Handler, policy: TracebackOptions) -> None:
    """
    Configure handler to include traceback policy in log records.
    
    Adds a filter to the handler that injects the specified traceback policy
    into all log records processed by this handler. This allows downstream
    components to determine how to render exception tracebacks.

    Args:
        handler: Handler to configure with the traceback policy.
        policy: Traceback policy to apply to all records from this handler.
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
