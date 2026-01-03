from typing import Optional
from .span import Span

class Tracer(object):
    ...

    def current_span(self) -> Optional[Span]:
        ...