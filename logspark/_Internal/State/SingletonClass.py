from typing import Any, Dict


class SingletonMeta(type):
    """Metaclass that enforces one instance per class.

    Classes that use ``metaclass=SingletonMeta`` return the same object on
    every instantiation call. The first call creates and caches the instance;
    subsequent calls return the cached one without invoking ``__init__`` again.

    Instances are keyed by their exact class, so two subclasses that both use
    ``SingletonMeta`` maintain independent singleton slots.

    The cached instance can be discarded by calling ``kill_instance()`` on the
    class. After that, the next instantiation creates a fresh object.
    """

    _s_instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._s_instances:
            cls._s_instances[cls] = super().__call__(*args, **kwargs)
        return cls._s_instances[cls]

    def kill_instance(cls) -> None:
        """Discard the cached singleton instance.

        After this call, the next ``cls()`` invocation creates and caches a
        new instance. Existing references to the old instance remain valid but
        will no longer be returned by future instantiation calls.
        """
        cls._s_instances.pop(cls, None)
