from typing import Optional, Union, Dict, Sequence
import logging

class BaseJsonFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Optional[Union[str, Sequence[str]]] = ...,
        datefmt: Optional[str] = ...,
        style: str = ...,
        validate: bool = True,
        *,
        prefix: str = ...,
        rename_fields: Optional[Dict[str, str]] = ...,
        rename_fields_keep_missing: bool = False,
        static_fields: Optional[Dict[str, object]] = ...,
        reserved_attrs: Optional[Sequence[str]] = ...,
        timestamp: Union[bool, str] = False,
        defaults: Optional[Dict[str, object]] = ...,
        exc_info_as_array: bool = False,
        stack_info_as_array: bool = False,
    ) -> None: ...
