import logging
from typing import Any, Optional

from .._Internal.Func import emit_warning
from .._Internal.State.Env import is_dependency_available
from ..Types import MissingDependencyWarning


class DDTraceInjectionFilter(logging.Filter):
    """
    Filter that opportunistically injects ddtrace trace and span IDs into log records.

    When a ddtrace span is active, ``dd_trace_id`` and ``dd_span_id`` are
    written onto the record for correlation with APM traces. Failures are
    swallowed silently — this filter never blocks a record or raises.

    ddtrace is resolved lazily on the first ``filter()`` call to avoid the
    significant startup cost of importing it at module load time. When ddtrace
    is not installed a one-time ``MissingDependencyWarning`` is emitted and
    subsequent calls are no-ops.
    """

    _tracer: Optional[Any] = None
    _tracer_checked: bool = False

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject ddtrace correlation fields when an active span exists; always returns True."""
        try:
            if not self._tracer_checked:
                DDTraceInjectionFilter._tracer_checked = True
                if is_dependency_available("ddtrace"):
                    from ddtrace.trace import tracer as _t  # type: ignore[import-unresolved]

                    DDTraceInjectionFilter._tracer = _t
                else:
                    emit_warning(
                        message=(
                            "\nWARNING: DDTrace injection requested but DDTrace is not installed.\n"
                            "  | No trace association will be available.\n"
                        ),
                        category=MissingDependencyWarning,
                        stacklevel=4,
                    )

            if self._tracer is not None:
                current_span = self._tracer.current_span()
                if current_span is not None:
                    record.dd_trace_id = current_span.trace_id
                    record.dd_span_id = current_span.span_id
        except Exception:
            pass

        return True
