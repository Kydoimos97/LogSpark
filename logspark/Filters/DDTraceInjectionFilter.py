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
    Filter that opportunistically injects ddtrace trace and span IDs into log records.

    When a ddtrace span is active, ``dd_trace_id`` and ``dd_span_id`` are
    written onto the record for correlation with APM traces. Failures are
    swallowed silently — this filter never blocks a record or raises.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject ddtrace correlation fields when an active span exists; always returns True."""
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
