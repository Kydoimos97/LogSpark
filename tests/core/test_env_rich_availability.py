"""Tests for Env.py is_rich_available function (lines 26-28)."""

from unittest.mock import patch

from logspark._Internal.State.Env import is_rich_available


class TestEnvRichAvailability:
    """Test is_rich_available function exception handling."""

    def test_is_rich_available_value_error_handling(self):
        """Test that ValueError in find_spec returns False (lines 26-28)."""
        with patch('logspark._Internal.State.Env.find_spec', side_effect=ValueError("Mock error")):
            result = is_rich_available()
            assert result is False

    def test_is_rich_available_when_rich_present(self):
        """Test that is_rich_available returns True when rich is available."""
        with patch('logspark._Internal.State.Env.find_spec', return_value=object()):
            result = is_rich_available()
            assert result is True

    def test_is_rich_available_when_rich_absent(self):
        """Test that is_rich_available returns False when rich is not available."""
        with patch('logspark._Internal.State.Env.find_spec', return_value=None):
            result = is_rich_available()
            assert result is False