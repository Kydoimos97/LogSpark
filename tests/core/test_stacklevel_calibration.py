"""Tests for resolve_stacklevel calibration (lines 38-46, 71)."""

import os
from unittest.mock import patch

from logspark._Internal.Func.resolve_stacklevel import _calibrate_fast_stacklevel, resolve_stacklevel


class TestStacklevelCalibration:
    """Test stacklevel calibration functions."""

    def test_calibrate_fast_stacklevel_execution(self):
        """Test that _calibrate_fast_stacklevel executes the calibration loop (lines 38-46)."""
        # Clear any cached value to force calibration
        from logspark._Internal.Func import resolve_stacklevel as module
        original_cached = getattr(module, '_CACHED_SL', None)
        module._CACHED_SL = None
        
        try:
            # Call the calibration function
            result = _calibrate_fast_stacklevel()
            
            # Should return an integer stacklevel
            assert isinstance(result, int)
            assert result > 0
            
        finally:
            # Restore original cached value
            module._CACHED_SL = original_cached

    def test_resolve_stacklevel_exception_handling(self):
        """Test exception handling in resolve_stacklevel (line 71)."""
        # Mock sys._getframe to raise ValueError
        with patch('sys._getframe', side_effect=ValueError("Mock frame error")):
            # Should fall back to cached stacklevel without error
            result = resolve_stacklevel(1)
            
            # Should return a valid stacklevel (fallback behavior)
            assert isinstance(result, int)
            assert result > 0

    def test_resolve_stacklevel_normal_mode(self):
        """Test resolve_stacklevel in normal (non-fast) mode."""
        # Ensure we're not in fast mode
        with patch.dict(os.environ, {}, clear=True):  # Clear LOGSPARK_MODE
            result = resolve_stacklevel(1)
            
            # Should return a valid stacklevel
            assert isinstance(result, int)
            assert result >= 1