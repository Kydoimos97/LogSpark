import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass  # type: ignore[import-unresolved]

_dd_tracer: Optional[Any] = None

try:
    from ddtrace.trace import tracer as _dd_tracer  # type: ignore[import-unresolved]
except ImportError:  # pragma: no cover
    pass  # pragma: no cover


class DDTraceInjectionFilter(logging.Filter):
    """
    Stage that opportunistically injects ddtrace correlation fields

    This Stage enriches LogRecord instances with ddtrace correlation data
    when ddtrace is active. It never forces JSON output or mutates handlers.
    """

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
