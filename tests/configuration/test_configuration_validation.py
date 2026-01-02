"""
Tests for validate_configuration_parameters function.

Tests parameter validation, invalid combinations, and preset/handler precedence.
"""

import logging

import pytest

from logspark._Internal.Func import validate_configuration_parameters
from logspark.Types import InvalidConfigurationError, PresetOptions, TracebackOptions


class TestValidateConfigurationParameters:
    """Test validate_configuration_parameters function behavior."""

    def test_valid_parameters_all_specified(self):
        """Test validation with all valid parameters specified."""
        handler = logging.StreamHandler()
        level, traceback, preset = validate_configuration_parameters(
            level=logging.INFO,
            traceback=TracebackOptions.COMPACT,
            handler=handler,
            preset=PresetOptions.TERMINAL,
            no_freeze=False,
        )

        assert level == logging.INFO
        assert traceback == TracebackOptions.COMPACT
        assert preset == PresetOptions.TERMINAL

    def test_valid_parameters_minimal(self):
        """Test validation with minimal valid parameters."""
        level, traceback, preset = validate_configuration_parameters(
            level=logging.WARNING, traceback=None, handler=None, preset=None, no_freeze=True
        )

        assert level == logging.WARNING
        assert traceback == TracebackOptions.NONE
        assert preset is None

    def test_string_level_conversion(self):
        """Test that string levels are converted to integers."""
        level, _, _ = validate_configuration_parameters(
            level="DEBUG", traceback=None, handler=None, preset=None, no_freeze=False
        )

        assert level == logging.DEBUG

    def test_string_traceback_conversion(self):
        """Test that string traceback options are converted to enums."""
        _, traceback, _ = validate_configuration_parameters(
            level=logging.INFO, traceback="full", handler=None, preset=None, no_freeze=False
        )

        assert traceback == TracebackOptions.FULL

    def test_string_preset_conversion(self):
        """Test that string preset options are converted to enums."""
        _, _, preset = validate_configuration_parameters(
            level=logging.INFO, traceback=None, handler=None, preset="json", no_freeze=False
        )

        assert preset == PresetOptions.JSON

    def test_case_insensitive_traceback(self):
        """Test that traceback options are case insensitive."""
        test_cases = [
            ("NONE", TracebackOptions.NONE),
            ("none", TracebackOptions.NONE),
            ("None", TracebackOptions.NONE),
            ("COMPACT", TracebackOptions.COMPACT),
            ("compact", TracebackOptions.COMPACT),
            ("Compact", TracebackOptions.COMPACT),
            ("FULL", TracebackOptions.FULL),
            ("full", TracebackOptions.FULL),
            ("Full", TracebackOptions.FULL),
        ]

        for input_str, expected in test_cases:
            _, traceback, _ = validate_configuration_parameters(
                level=logging.INFO, traceback=input_str, handler=None, preset=None, no_freeze=False
            )
            assert traceback == expected

    def test_case_insensitive_preset(self):
        """Test that preset options are case insensitive."""
        test_cases = [
            ("TERMINAL", PresetOptions.TERMINAL),
            ("terminal", PresetOptions.TERMINAL),
            ("Terminal", PresetOptions.TERMINAL),
            ("JSON", PresetOptions.JSON),
            ("json", PresetOptions.JSON),
            ("Json", PresetOptions.JSON),
        ]

        for input_str, expected in test_cases:
            _, _, preset = validate_configuration_parameters(
                level=logging.INFO, traceback=None, handler=None, preset=input_str, no_freeze=False
            )
            assert preset == expected

    def test_invalid_level_raises_error(self):
        """Test that invalid levels raise KeyError."""
        with pytest.raises(KeyError):
            validate_configuration_parameters(
                level=999,  # Invalid level
                traceback=None,
                handler=None,
                preset=None,
                no_freeze=False,
            )

    def test_invalid_traceback_string_raises_error(self):
        """Test that invalid traceback strings raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="Invalid traceback option"):
            validate_configuration_parameters(
                level=logging.INFO, traceback="invalid", handler=None, preset=None, no_freeze=False
            )

    def test_invalid_traceback_type_raises_error(self):
        """Test that invalid traceback types raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="Invalid traceback"):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback=123,  # Invalid type
                handler=None,
                preset=None,
                no_freeze=False,
            )

    def test_invalid_preset_string_raises_error(self):
        """Test that invalid preset strings raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="Invalid preset option"):
            validate_configuration_parameters(
                level=logging.INFO, traceback=None, handler=None, preset="invalid", no_freeze=False
            )

    def test_invalid_preset_type_raises_error(self):
        """Test that invalid preset types raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="Invalid preset option"):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback=None,
                handler=None,
                preset=123,  # Invalid type
                no_freeze=False,
            )

    def test_invalid_handler_type_raises_error(self):
        """Test that invalid handler types raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="handler must be a logging.Handlers instance"
        ):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback=None,
                handler="not_a_handler",  # Invalid type
                preset=None,
                no_freeze=False,
            )

    def test_invalid_no_freeze_type_raises_error(self):
        """Test that invalid no_freeze types raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="no_freeze must be a bool"):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback=None,
                handler=None,
                preset=None,
                no_freeze="not_a_bool",  # Invalid type
            )

    def test_handler_precedence_over_preset(self):
        """Test that explicit handler takes precedence over preset."""
        # When both handler and preset are provided, both should be validated
        # but the function should return the preset as-is (precedence is handled elsewhere)
        handler = logging.StreamHandler()
        level, traceback, preset = validate_configuration_parameters(
            level=logging.INFO,
            traceback=None,
            handler=handler,
            preset=PresetOptions.JSON,
            no_freeze=False,
        )

        # Both should be preserved - precedence logic is handled by caller
        assert preset == PresetOptions.JSON

    def test_none_traceback_defaults_to_none_enum(self):
        """Test that None traceback defaults to TracebackOptions.NONE."""
        _, traceback, _ = validate_configuration_parameters(
            level=logging.INFO, traceback=None, handler=None, preset=None, no_freeze=False
        )

        assert traceback == TracebackOptions.NONE

    def test_valid_handler_instance(self):
        """Test that valid handler instances are accepted."""
        handlers = [
            logging.StreamHandler(),
            logging.FileHandler("test.log"),
            logging.NullHandler(),
        ]

        for handler in handlers:
            # Should not raise any exception
            validate_configuration_parameters(
                level=logging.INFO, traceback=None, handler=handler, preset=None, no_freeze=False
            )
            # Clean up file handler if created
            if hasattr(handler, "close"):
                handler.close()


class TestParameterCombinations:
    """Test invalid parameter combinations."""

    def test_conflicting_traceback_formats(self):
        """Test behavior with conflicting traceback and format specifications."""
        # This tests that the function validates each parameter independently
        # Conflict resolution is handled by the caller
        handler = logging.StreamHandler()

        # Should validate successfully - conflict resolution is caller's responsibility
        level, traceback, preset = validate_configuration_parameters(
            level=logging.INFO,
            traceback=TracebackOptions.FULL,
            handler=handler,
            preset=PresetOptions.JSON,  # JSON might have different traceback handling
            no_freeze=False,
        )

        assert traceback == TracebackOptions.FULL
        assert preset == PresetOptions.JSON

    def test_edge_case_empty_string_traceback(self):
        """Test that empty string traceback raises appropriate error."""
        with pytest.raises(InvalidConfigurationError):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback="",  # Empty string
                handler=None,
                preset=None,
                no_freeze=False,
            )

    def test_edge_case_empty_string_preset(self):
        """Test that empty string preset raises appropriate error."""
        with pytest.raises(InvalidConfigurationError):
            validate_configuration_parameters(
                level=logging.INFO,
                traceback=None,
                handler=None,
                preset="",  # Empty string
                no_freeze=False,
            )
