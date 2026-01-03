from typing import Dict, Optional, Union
from .color import Color

class Style:
    def __init__(
        self,
        color: Optional[Union[Color, str]] = ...,
        bgcolor: Optional[Union[Color, str]] = ...,
        bold: Optional[bool] = ...,
        dim: Optional[bool] = ...,
        italic: Optional[bool] = ...,
        underline: Optional[bool] = ...,
        blink: Optional[bool] = ...,
        blink2: Optional[bool] = ...,
        reverse: Optional[bool] = ...,
        conceal: Optional[bool] = ...,
        strike: Optional[bool] = ...,
        underline2: Optional[bool] = ...,
        frame: Optional[bool] = ...,
        encircle: Optional[bool] = ...,
        overline: Optional[bool] = ...,
        link: Optional[str] = ...,
        meta: Optional[Dict[str, object]] = ...,
    ) -> None: ...

    @classmethod
    def null(cls) -> "Style": ...
