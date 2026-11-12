import logging
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import Any, Iterator, Mapping

_BOUND_FIELDS: ContextVar[Mapping[str, Any]] = ContextVar(
    "logspark_bound_context", default=MappingProxyType({})
)

# Names a field may not take on a record: every attribute and method of a LogRecord, plus the
# two attributes a formatter adds while formatting.
_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        *dir(logging.LogRecord("", logging.NOTSET, "", 0, "", None, None)),
        "message",
        "asctime",
    }
)


@contextmanager
def bound_context(**fields: Any) -> Iterator[None]:
    """
    Bind context fields to every log record emitted inside the block.

    Backed by ``contextvars``, so the binding is local to the current thread
    or asyncio task and is inherited by tasks started inside the block. Blocks
    nest: fields bound by an outer block stay bound, an inner field of the same
    name wins, and the previous bindings are restored on exit, also on error.

    Binding alone changes no output. ``ContextFilter`` copies the bound fields
    onto records; attach it to a handler or a logger.
    """
    token = _BOUND_FIELDS.set(MappingProxyType({**_BOUND_FIELDS.get(), **fields}))
    try:
        yield
    finally:
        _BOUND_FIELDS.reset(token)


def get_bound_context() -> Mapping[str, Any]:
    """Return a read-only view of the fields bound in the current context."""
    return _BOUND_FIELDS.get()


class ContextFilter(logging.Filter):
    """
    Filter that copies the fields bound with ``bound_context`` onto each record.

    The fields become record attributes, so ``SparkJsonHandler`` writes them as
    JSON keys and a stdlib format string can name them. Always returns True.

    A field never replaces something the record already carries:

    - a field passed with ``extra=`` on the log call wins over a bound field
      of the same name;
    - a field whose name is a ``LogRecord`` attribute (``name``, ``msg``,
      ``args``, ``message``, ``asctime`` and so on) is written under
      ``clash_prefix`` plus the name instead.

    Attach the filter to a handler to cover every record that handler emits,
    including records that third-party loggers propagate to it. A filter on a
    logger sees only the records logged through that logger itself.
    """

    def __init__(self, name: str = "", clash_prefix: str = "ctx_") -> None:
        """Initialize with the prefix used for fields that clash with a LogRecord attribute."""
        super().__init__(name)
        if not clash_prefix:
            raise ValueError("clash_prefix must not be empty")
        self.clash_prefix = clash_prefix

    def filter(self, record: logging.LogRecord) -> bool:
        """Copy the bound fields onto the record; always returns True."""
        for name, value in _BOUND_FIELDS.get().items():
            key = f"{self.clash_prefix}{name}" if name in _RESERVED_NAMES else name
            if not hasattr(record, key):
                setattr(record, key, value)
        return True
