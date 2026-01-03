from typing import Optional, Callable, Union
import json
from .core import BaseJsonFormatter


class JsonFormatter(BaseJsonFormatter):
    def __init__(
        self,
        *args: object,
        json_default: Optional[Callable[..., object]] = ...,
        json_encoder: Optional[Callable[..., object]] = ...,
        json_serializer: Callable[..., str] = ...,
        json_indent: Optional[Union[int, str]] = ...,
        json_ensure_ascii: bool = ...,
        **kwargs: object,
    ) -> None: ...
