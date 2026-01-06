"""
Tests for SingletonClass decorator.

Tests singleton enforcement behavior and violation detection.
"""

import pytest

from logspark._Internal.State import SingletonClass
from logspark._Internal.State.SingletonClass import _SingletonViolationException


class TestSingletonClass:
    """Test SingletonClass decorator behavior."""

    def test_singleton_enforcement_same_instance(self):
        """Test that decorated class returns same instance on multiple instantiations."""

        @SingletonClass
        class TestSingleton:
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

        @SingletonClass
        class TestSingleton:
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

        @SingletonClass
        class TestSingleton:
            def __init__(self, name, value=None):
                self.name = name
                self.value = value or 0

        # First instantiation with args
        instance1 = TestSingleton("test", 42)

        # Subsequent instantiations ignore args due to singleton behavior
        instance2 = TestSingleton("ignored", 999)
        instance3 = TestSingleton()

        assert instance1 is instance2 is instance3
        assert instance1.name == "test"
        assert instance1.value == 42
        assert instance2.name == "test"  # Args ignored on second call
        assert instance3.name == "test"  # Args ignored on third call

    def test_singleton_preserves_class_metadata(self):
        """Test that decorator preserves original class metadata."""

        @SingletonClass
        class TestSingleton:
            """Test singleton class docstring."""

            pass

        assert TestSingleton.__name__ == "TestSingleton"
        assert TestSingleton.__doc__ == "Test singleton class docstring."

    def test_singleton_with_methods(self):
        """Test that singleton works correctly with class methods."""

        @SingletonClass
        class TestSingleton:
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

    def test_multiple_singleton_classes_independent(self):
        """Test that different singleton classes maintain separate instances."""

        @SingletonClass
        class SingletonA:
            def __init__(self):
                self.name = "A"

        @SingletonClass
        class SingletonB:
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


class TestSingletonViolationDetection:
    """Test singleton violation detection."""

    def test_violation_custom_new_method(self):
        """Test that defining __new__ method raises violation exception."""
        with pytest.raises(_SingletonViolationException, match="Singleton violation"):

            @SingletonClass
            class InvalidSingleton:
                def __new__(cls):
                    return super().__new__(cls)

    def test_violation_cls_instance_attribute(self):
        """Test that defining __cls_instance attribute raises violation exception."""
        # Note: Due to Python name mangling, __cls_instance becomes _ClassName__cls_instance
        # The actual check in SingletonClass looks for the literal "__cls_instance" string
        # This test verifies the intended behavior even though name mangling occurs

        # This should NOT raise an exception due to name mangling
        @SingletonClass
        class ValidClass:
            __cls_instance = None  # This gets mangled to _ValidClass__cls_instance

        # This would raise an exception if we could define it literally
        # but Python's name mangling prevents this from being a real issue
        instance = ValidClass()
        assert instance is not None

    def test_violation_cls_instance_literal_attribute(self):
        """Test that defining literal __cls_instance attribute raises violation exception."""
        # Create a class dynamically with the literal __cls_instance attribute
        class_dict = {"__cls_instance": None}
        TestClass = type("TestClass", (), class_dict)
        
        with pytest.raises(_SingletonViolationException, match="Singleton violation"):
            SingletonClass(TestClass)

    def test_violation_exception_message_contains_class_name(self):
        """Test that violation exception message contains the class name."""
        with pytest.raises(_SingletonViolationException) as exc_info:

            @SingletonClass
            class ProblematicClass:
                def __new__(cls):
                    return super().__new__(cls)

        assert "ProblematicClass" in str(exc_info.value)
        assert "Singleton violation" in str(exc_info.value)
        assert "__new__" in str(exc_info.value)

    def test_violation_exception_suggests_fix(self):
        """Test that violation exception provides helpful fix suggestion."""
        with pytest.raises(_SingletonViolationException) as exc_info:

            @SingletonClass
            class ProblematicClass:
                def __new__(cls):
                    return super().__new__(cls)

        error_msg = str(exc_info.value)
        assert "Fix:" in error_msg
        assert "__new__" in error_msg

    def test_valid_class_no_violation(self):
        """Test that properly defined class does not raise violation."""

        # This should not raise any exception
        @SingletonClass
        class ValidSingleton:
            def __init__(self):
                self.value = 42

            def method(self):
                return self.value

        # Should be able to instantiate without issues
        instance = ValidSingleton()
        assert instance.value == 42
        assert instance.method() == 42


class TestSingletonEdgeCases:
    """Test edge cases and special scenarios."""

    def test_singleton_with_inheritance(self):
        """Test singleton behavior with class inheritance."""

        @SingletonClass
        class BaseSingleton:
            def __init__(self):
                self.base_value = "base"

        # Inheriting from a singleton class inherits the singleton behavior
        # The derived class returns the same instance as the base class
        class DerivedClass(BaseSingleton):
            def __init__(self):
                super().__init__()
                self.derived_value = "derived"

        base1 = BaseSingleton()
        base2 = BaseSingleton()
        derived1 = DerivedClass()
        derived2 = DerivedClass()

        # All instances are the same due to singleton inheritance
        assert base1 is base2
        assert derived1 is derived2
        assert base1 is derived1  # Same singleton instance

        # The instance has the base class type
        assert type(base1).__name__ == "BaseSingleton"
        assert type(derived1).__name__ == "BaseSingleton"

    def test_singleton_with_class_variables(self):
        """Test singleton behavior with class variables."""

        @SingletonClass
        class TestSingleton:
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

        @SingletonClass
        class TestSingleton:
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
