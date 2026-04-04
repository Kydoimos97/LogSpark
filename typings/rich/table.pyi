from .console import ConsoleRenderable, RenderableType

class Table(ConsoleRenderable):
    @classmethod
    def grid(
        cls,
        *args: object,
        **kwargs: object,
    ) -> "Table": ...

    def add_column(
        self,
        *args: object,
        **kwargs: object,
    ) -> None: ...

    def add_row(
        self,
        *renderables: RenderableType,
        **kwargs: object,
    ) -> None: ...
