from typing import Any

from .console import ConsoleRenderable, RenderableType

class Table(ConsoleRenderable):
    @classmethod
    def grid(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> "Table": ...
    def add_column(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def add_row(
        self,
        *renderables: RenderableType,
        **kwargs: Any,
    ) -> None: ...
