"""Tests for LogManagerState.__post_init__ edge case (line 13)."""

from logspark._Internal.State.LogManagerState import LogManagerState


class TestLogManagerStatePostInit:
    """Test LogManagerState.__post_init__ method."""

    def test_post_init_when_managed_loggers_is_none(self):
        """Test __post_init__ initializes managed_loggers when None (line 13)."""
        # Create instance without managed_loggers
        state = LogManagerState.__new__(LogManagerState)
        
        # Manually set managed_loggers to None to trigger the condition
        state.managed_loggers = None
        
        # Call __post_init__
        state.__post_init__()
        
        # Should initialize to empty dict
        assert state.managed_loggers == {}

    def test_post_init_preserves_existing_managed_loggers(self):
        """Test __post_init__ preserves existing managed_loggers."""
        # Create instance with existing managed_loggers
        existing_loggers = {"test": "logger"}
        state = LogManagerState(managed_loggers=existing_loggers)
        
        # Call __post_init__ again
        state.__post_init__()
        
        # Should preserve existing value
        assert state.managed_loggers is existing_loggers