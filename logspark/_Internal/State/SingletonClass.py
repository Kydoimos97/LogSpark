from typing import Any, Protocol, TypeVar, cast

from typing_extensions import runtime_checkable


@runtime_checkable
class IsSingletonClassInstance(Protocol):
    _cls_instance: Any

    @classmethod
    def _kill_instance(cls) -> None: ...


TAny = TypeVar("TAny", bound=Any)
T = TypeVar("T", bound=IsSingletonClassInstance)


class _SingletonViolationException(Exception):
    def __init__(self, cls: type[Any]) -> None:
        cls_name = getattr(cls, "__name__", "<unknown class>")
        super().__init__(
            f"Singleton violation in '{cls_name}':\n"
            f"  Classes decorated with @SingletonClass must not override '__new__'\n"
            f"  or define '_cls_instance'."
        )


def SingletonClass(cls: type[TAny]) -> type[T]:  # noqa: N802
    if "__new__" in cls.__dict__ or "_cls_instance" in cls.__dict__:
        raise _SingletonViolationException(cls)

    # noinspection PyMethodParameters
    class SingletonPattern(cls):  # type: ignore[valid-type,misc]
        _cls_instance = None

        def __new__(cls_, *args: Any, **kwargs: Any) -> Any:
            if cls_._cls_instance is None:
                cls_._cls_instance = super().__new__(cls_)
            return cls_._cls_instance

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            if not getattr(self, "__singleton_initialized__", False):
                super().__init__(*args, **kwargs)
                self.__singleton_initialized__ = True

        # noinspection PyUnusedFunction
        @classmethod
        def _kill_instance(cls_: type[T]) -> None:
            cls_._cls_instance = None

    SingletonPattern.__name__ = cls.__name__
    SingletonPattern.__qualname__ = cls.__qualname__
    SingletonPattern.__doc__ = cls.__doc__

    # noinspection PyUnnecessaryCast
    return cast(type[T], SingletonPattern)
