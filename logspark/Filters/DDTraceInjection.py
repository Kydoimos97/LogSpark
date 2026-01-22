import logging
from typing import TYPE_CHECKING, Any, Optional

from .._Internal import SparkFilterModule

if TYPE_CHECKING:
    from ddtrace.trace import Tracer

_dd_tracer: Optional["Tracer"] = None

try:
    from ddtrace.trace import tracer

    _dd_tracer = tracer
except ImportError:  # pragma: no cover
    _dd_tracer = None  # pragma: no cover


class DDTraceInjection(SparkFilterModule):
    """
    Stage that opportunistically injects ddtrace correlation fields

    This Stage enriches LogRecord instances with ddtrace correlation data
    when ddtrace is active. It never forces JSON output or mutates handlers.
    """

    def configure(self, **kwargs: Any) -> None:
        pass

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject ddtrace correlation fields if ddtrace is active

        Args:
            record: LogRecord to potentially enrich

        Returns:
            True (always allow record to pass through)
        """
        try:
            # Opportunistic ddtrace import - only inject if available and active
            # noinspection PyUnresolvedReferences
            if _dd_tracer is not None:
                # Get current span if active
                current_span = _dd_tracer.current_span()
                if current_span is not None:
                    # Inject correlation fields into LogRecord
                    record.dd_trace_id = current_span.trace_id
                    record.dd_span_id = current_span.span_id
            else:
                # DDTrace not installed so pass
                pass
        except Exception:
            # Any other ddtrace error - fail silently to avoid breaking logging
            pass

        return True
