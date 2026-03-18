"""
Test LogManagerState functionality.
"""

import logging

from logspark._Internal.State.LogManagerState import LogManagerState


class TestLogManagerState:
    """Test LogManagerState dataclass"""

    def test_default_initialization(self):
        """Test LogManagerState with default managed_loggers"""
        state = LogManagerState(managed_loggers={})
        assert state.managed_loggers == {}

    def test_initialization_with_loggers(self):
        """Test LogManagerState with provided loggers"""
        logger = logging.getLogger("test")
        loggers = {"test": logger}
        state = LogManagerState(managed_loggers=loggers)
        assert state.managed_loggers == loggers

    def test_post_init_with_none_managed_loggers(self):
        """Test __post_init__ when managed_loggers is None"""
        # Create instance without calling __init__ to simulate None case
        state = LogManagerState.__new__(LogManagerState)
        # Manually set managed_loggers to None to trigger the condition
        state.managed_loggers = None
        state.__post_init__()
        assert state.managed_loggers == {}

    def test_post_init_with_existing_managed_loggers(self):
        """Test __post_init__ when managed_loggers already exists"""
        logger = logging.getLogger("test")
        loggers = {"test": logger}
        state = LogManagerState(managed_loggers=loggers)
        # Should not change existing loggers
        assert state.managed_loggers == loggers