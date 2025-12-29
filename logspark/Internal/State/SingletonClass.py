#  Copyright (c) 2024-2025.
#  Author: Willem van der Schans.
#  Licensed under the MIT License (https://opensource.org/license/mit).
from typing import Any, Type, TypeVar, cast

T = TypeVar("T")


class _SingletonViolationException(Exception):
    """
    Raised when a class using @SingletonClass improperly defines its own __new__ method.
    """

    def __init__(self, cls: Type[Any]) -> None:
        cls_name = getattr(cls, "__name__", "<unknown class>")
        msg = (
            f"Singleton violation in '{cls_name}':\n"
            f"  Classes decorated with @SingletonClass must not override the "
            f"'__new__' method or define a __cls_instance attribute.\n"
            f"  This breaks singleton enforcement and leads to unexpected behavior.\n"
            f"\n  ➤ Fix: Remove the '__new__' method and __cls_instance attribute "
            f"or do not use the @SingletonClass decorator.\n"
        )
        super().__init__(msg)


def SingletonClass(cls: Type[T]) -> Type[T]:
    """
    Enforces singleton behavior by wrapping the class in a custom subclass.

    Prevents the user-defined class from defining its own `__new__`, which would
    conflict with the singleton logic.

    :return: A singleton-enforcing subclass of the original
    """
    if "__new__" in cls.__dict__:
        raise _SingletonViolationException(cls)
    if "__cls_instance" in cls.__dict__:
        raise _SingletonViolationException(cls)

    class SingletonWrapper(cls):  # type: ignore[misc, valid-type]
        __cls_instance = None

        def __new__(cls_, *args: Any, **kwargs: Any) -> Any:
            if cls_.__cls_instance is None:
                cls_.__cls_instance = super(SingletonWrapper, cls_).__new__(cls_)
            return cls_.__cls_instance

        def __init__(self, *args: Any, **kwargs: Any):
            if not getattr(self, "__singleton_initialized__", False):
                super(SingletonWrapper, self).__init__(*args, **kwargs)
                setattr(self, "__singleton_initialized__", True)

    SingletonWrapper.__name__ = cls.__name__
    SingletonWrapper.__qualname__ = cls.__qualname__
    SingletonWrapper.__doc__ = cls.__doc__
    return cast(Type[T], SingletonWrapper)
