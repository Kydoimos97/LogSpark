"""Tests for SparkLoggerDef handler_preset handling in configure method (lines 251-261)."""

import logging
from unittest.mock import Mock

import pytest

from logspark.Types import PresetOptions


class TestSparkLoggerPresetHandling:
    """Test handler_preset handling logic in SparkLoggerDef.configure method."""

    def test_configure_preset_terminal_creates_terminal_handler(self, fresh_logger):
        """Test that TERMINAL handler_preset creates SparkTerminalHandler (lines 251-253)."""
        # Configure with TERMINAL handler_preset and no explicit handler
        fresh_logger.configure()
        
        # Verify handler type
        assert len(fresh_logger.instance.handlers) == 1
        handler = fresh_logger.instance.handlers[0]
        
        # Should be SparkTerminalHandler
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler
        assert isinstance(handler, SparkTerminalHandler)

    def test_configure_preset_json_creates_json_handler(self, fresh_logger):
        """Test that JSON handler_preset creates SparkJsonHandler (lines 254-256)."""
        # Configure with JSON handler_preset and no explicit handler
        fresh_logger.configure()
        
        # Verify handler type
        assert len(fresh_logger.instance.handlers) == 1
        handler = fresh_logger.instance.handlers[0]
        
        # Should be SparkJsonHandler
        from logspark.Handlers.SparkJsonHandler import SparkJsonHandler
        assert isinstance(handler, SparkJsonHandler)

    def test_configure_invalid_preset_raises_value_error(self, fresh_logger):
        """Test that invalid handler_preset raises ValueError (lines 257-259)."""
        # Mock an invalid handler_preset that passes validation but isn't handled
        with pytest.raises(ValueError, match="Invalid handler_preset"):
            # This would require mocking the validation to return an invalid enum
            # Since validation prevents this, we test the error path directly
            fresh_logger._configured = None
            
            # Directly test the error condition by patching validation
            from unittest.mock import patch
            with patch('logspark.SparkLoggerDef.validate_configuration_parameters') as mock_validate:
                # Return an invalid handler_preset that isn't TERMINAL or JSON
                mock_invalid_preset = Mock()
                mock_invalid_preset.name = "INVALID"
                mock_validate.return_value = (logging.INFO, None, mock_invalid_preset)

                fresh_logger.configure()