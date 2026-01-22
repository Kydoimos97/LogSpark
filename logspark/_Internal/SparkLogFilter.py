import logging
from abc import ABC, abstractmethod
from typing import Any


class SparkFilterModule(ABC, logging.Filter):
    _inject: bool = False

    def __init__(self, name: str = ""):
        if not name:
            name = self.__class__.__name__
        super().__init__(name)
        self._ext_init()

    def _ext_init(self) -> None: ...

    @property
    def inject(self) -> bool:
        return self._inject

    def set_injection(self, inject: bool) -> None:
        """
        Injection refers to injecting information into native log record fields
        making it explicitly possible to violate Liskov substitution principle.
        """
        self._inject = inject

    @abstractmethod
    def configure(self, **kwargs: Any) -> None: ...
