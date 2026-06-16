"""
Tests for SingletonMeta metaclass.

Tests singleton enforcement behavior via the SingletonMeta metaclass,
instance tracking, and lifecycle management.
"""

from typing import Any, cast

from logspark._Internal.State import SingletonMeta
from logspark.Types import is_singleton


def kill_if_singleton(instance: object) -> None:
    """Kill instance if it's a singleton, no-op otherwise."""
    if is_singleton(instance):
        cast(Any, type(instance)).kill_instance()


class TestSingletonMetaEnforcement:
    """Test SingletonMeta metaclass singleton enforcement."""

    def test_singleton_enforcement_same_instance(self):
        """Test that metaclass returns same instance on multiple instantiations."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 42

        instance1 = TestSingleton()
        instance2 = TestSingleton()

        assert instance1 is instance2
        assert instance1.value == 42
        assert instance2.value == 42

    def test_singleton_initialization_once(self):
        """Test that __init__ is called only once even with multiple instantiations."""
        init_count = 0

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                nonlocal init_count
                init_count += 1
                self.value = init_count

        instance1 = TestSingleton()
        instance2 = TestSingleton()
        instance3 = TestSingleton()

        assert init_count == 1
        assert instance1.value == 1
        assert instance2.value == 1
        assert instance3.value == 1
        assert instance1 is instance2 is instance3

    def test_singleton_with_constructor_args(self):
        """Test singleton behavior with constructor arguments."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self, name: str = "", value: int | None = None):
                self.name = name
                self.value = value or 0

        # First instantiation with args
        instance1 = TestSingleton("test", 42)

        # Subsequent instantiations ignore args due to singleton behavior
        # SingletonMeta.__call__ always returns cached instance, ignoring new args
        instance2 = TestSingleton("ignored", 999)
        instance3 = TestSingleton()

        assert instance1 is instance2 is instance3
        assert instance1.name == "test"
        assert instance1.value == 42
        assert instance2.name == "test"  # Args ignored on second call
        assert instance3.name == "test"  # Args ignored on third call

    def test_singleton_with_methods(self):
        """Test that singleton works correctly with instance methods."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.counter = 0

            def increment(self):
                self.counter += 1
                return self.counter

            def get_counter(self):
                return self.counter

        instance1 = TestSingleton()
        instance2 = TestSingleton()

        # Modify state through one instance
        result1 = instance1.increment()
        assert result1 == 1

        # Verify state is shared
        assert instance2.get_counter() == 1

        # Modify through second instance
        result2 = instance2.increment()
        assert result2 == 2

        # Verify state is still shared
        assert instance1.get_counter() == 2


class TestMultipleSingletonClasses:
    """Test that different singleton classes maintain separate instances."""

    def test_multiple_singleton_classes_independent(self):
        """Test that different singleton classes maintain separate instances."""

        class SingletonA(metaclass=SingletonMeta):
            def __init__(self):
                self.name = "A"

        class SingletonB(metaclass=SingletonMeta):
            def __init__(self):
                self.name = "B"

        a1 = SingletonA()
        a2 = SingletonA()
        b1 = SingletonB()
        b2 = SingletonB()

        # Same class instances should be identical
        assert a1 is a2
        assert b1 is b2

        # Different class instances should be different
        assert a1 is not b1
        assert a2 is not b2

        # Verify separate state
        assert a1.name == "A"
        assert b1.name == "B"

    def test_singleton_instance_tracking(self):
        """Test that singleton instances are tracked correctly."""

        class SingletonX(metaclass=SingletonMeta):
            pass

        class SingletonY(metaclass=SingletonMeta):
            pass

        x = SingletonX()
        y = SingletonY()

        # Both should be in the metaclass instance dict
        assert SingletonX in SingletonMeta._s_instances
        assert SingletonY in SingletonMeta._s_instances
        assert SingletonMeta._s_instances[SingletonX] is x
        assert SingletonMeta._s_instances[SingletonY] is y


class TestSingletonLifecycle:
    """Test singleton lifecycle and reset behavior."""

    def test_kill_instance_clears_cached_instance(self):
        """Test that kill_instance() clears the cached instance."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 42

        instance1 = TestSingleton()
        assert instance1.value == 42

        # Kill the instance
        TestSingleton.kill_instance()

        # Next instantiation should create a new instance
        instance2 = TestSingleton()

        # They are different objects
        assert instance1 is not instance2

        # But same class, so values could be the same if not modified
        assert instance2.value == 42

    def test_kill_instance_allows_reinit(self):
        """Test that after kill_instance(), __init__ runs again on next call."""
        init_count = 0

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                nonlocal init_count
                init_count += 1
                self.count = init_count

        instance1 = TestSingleton()
        assert init_count == 1
        assert instance1.count == 1

        # Kill and create again
        TestSingleton.kill_instance()
        instance2 = TestSingleton()

        assert init_count == 2
        assert instance2.count == 2
        assert instance1 is not instance2

    def test_kill_instance_idempotent(self):
        """Test that calling kill_instance() multiple times is safe."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        instance1 = TestSingleton()

        # Kill multiple times — should not raise
        TestSingleton.kill_instance()
        TestSingleton.kill_instance()
        TestSingleton.kill_instance()

        # Should still be able to create new instance
        instance2 = TestSingleton()
        assert instance1 is not instance2


class TestIsSingleton:
    """Test is_singleton() helper function."""

    def test_is_singleton_returns_true_for_singleton_instance(self):
        """Test that is_singleton() returns True for metaclass instances."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        instance = TestSingleton()

        assert is_singleton(instance) is True

    def test_is_singleton_returns_false_for_plain_class(self):
        """Test that is_singleton() returns False for plain class instances."""

        class PlainClass:
            pass

        instance = PlainClass()

        assert is_singleton(instance) is False

    def test_is_singleton_distinguishes_singleton_from_plain(self):
        """Test that is_singleton() correctly distinguishes singleton from plain classes."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        class PlainClass:
            pass

        singleton_instance = TestSingleton()
        plain_instance = PlainClass()

        assert is_singleton(singleton_instance) is True
        assert is_singleton(plain_instance) is False


class TestKillIfSingleton:
    """Test kill_if_singleton() helper function."""

    def test_kill_if_singleton_kills_singleton_instance(self):
        """Test that kill_if_singleton() calls kill_instance() for singletons."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        instance1 = TestSingleton()

        # Kill using helper
        kill_if_singleton(instance1)

        # Next instantiation should be a new instance
        instance2 = TestSingleton()

        assert instance1 is not instance2

    def test_kill_if_singleton_no_op_for_plain_class(self):
        """Test that kill_if_singleton() is a no-op for plain class instances."""

        class PlainClass:
            pass

        instance = PlainClass()

        # Should not raise
        kill_if_singleton(instance)

        # Instance should be unchanged
        assert instance is instance

    def test_kill_if_singleton_with_init_count(self):
        """Test kill_if_singleton() allows reinitialization of singletons."""
        init_count = 0

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                nonlocal init_count
                init_count += 1

        instance1 = TestSingleton()
        assert init_count == 1

        # Kill using helper
        kill_if_singleton(instance1)

        # Next instantiation should trigger __init__ again
        _ = TestSingleton()
        assert init_count == 2


class TestSingletonSubclasses:
    """Test subclass behavior with SingletonMeta."""

    def test_subclass_with_metaclass_assignment_gets_separate_singleton(self):
        """Test that subclasses with explicit metaclass get their own singleton slot."""

        class BaseSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.name = "base"

        class DerivedSingleton(BaseSingleton, metaclass=SingletonMeta):
            def __init__(self):
                self.name = "derived"

        base = BaseSingleton()
        derived = DerivedSingleton()

        # Should be different instances
        assert base is not derived
        assert base.name == "base"
        assert derived.name == "derived"

        # Each should have its own singleton slot
        assert BaseSingleton in SingletonMeta._s_instances
        assert DerivedSingleton in SingletonMeta._s_instances
        assert SingletonMeta._s_instances[BaseSingleton] is base
        assert SingletonMeta._s_instances[DerivedSingleton] is derived

    def test_singleton_with_class_variables(self):
        """Test singleton behavior with class variables."""

        class TestSingleton(metaclass=SingletonMeta):
            class_var = "shared"

            def __init__(self):
                self.instance_var = "instance"

        instance1 = TestSingleton()
        instance2 = TestSingleton()

        # Both should be the same instance
        assert instance1 is instance2

        # Class variables should be accessible
        assert instance1.class_var == "shared"
        assert instance2.class_var == "shared"

        # Modifying class variable affects both (same instance)
        TestSingleton.class_var = "modified"
        assert instance1.class_var == "modified"
        assert instance2.class_var == "modified"

    def test_singleton_with_properties(self):
        """Test singleton behavior with property decorators."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self._value = 0

            @property
            def value(self):
                return self._value

            @value.setter
            def value(self, val):
                self._value = val

        instance1 = TestSingleton()
        instance2 = TestSingleton()

        assert instance1 is instance2

        # Test property access
        assert instance1.value == 0
        assert instance2.value == 0

        # Test property modification
        instance1.value = 42
        assert instance2.value == 42  # Same instance, so same value


class TestSingletonMetadataPreservation:
    """Test that SingletonMeta preserves class metadata."""

    def test_singleton_preserves_class_name(self):
        """Test that metaclass preserves original class name."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        assert TestSingleton.__name__ == "TestSingleton"

    def test_singleton_preserves_docstring(self):
        """Test that metaclass preserves original class docstring."""

        class TestSingleton(metaclass=SingletonMeta):
            """Test singleton class docstring."""

            pass

        assert TestSingleton.__doc__ == "Test singleton class docstring."

    def test_singleton_preserves_module(self):
        """Test that metaclass preserves module attribute."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        assert TestSingleton.__module__ is not None
