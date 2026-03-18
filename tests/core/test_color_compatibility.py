"""
Test color compatibility detection functionality.

Tests validate:
- FORCE_COLOR and NO_COLOR environment variable handling
- Stream-based color detection
- IDLE and Jupyter environment detection
- TTY_COMPATIBLE environment variable handling
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

from logspark._Internal.Func.is_color_compatible_terminal import is_color_compatible_terminal


class TestColorCompatibleTerminal:
    """Test is_color_compatible_terminal functionality"""

    def test_color_compatible_with_force_color(self):
        """Test that FORCE_COLOR enables color output"""
        with patch.dict("os.environ", {"FORCE_COLOR": "true"}):
            assert is_color_compatible_terminal() is True
        
        with patch.dict("os.environ", {"FORCE_COLOR": "1"}):
            assert is_color_compatible_terminal() is True
        
        with patch.dict("os.environ", {"FORCE_COLOR": ""}):
            assert is_color_compatible_terminal() is False

    def test_color_compatible_no_color_override(self):
        """Test that NO_COLOR disables color output"""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            assert is_color_compatible_terminal() is False
        
        with patch.dict("os.environ", {"NO_COLOR": ""}):
            assert is_color_compatible_terminal() is False

    def test_color_compatible_force_color_overrides_no_color(self):
        """Test that FORCE_COLOR takes precedence over NO_COLOR"""
        with patch.dict("os.environ", {"FORCE_COLOR": "true", "NO_COLOR": "1"}):
            assert is_color_compatible_terminal() is True

    def test_color_compatible_tty_compatible_override(self):
        """Test TTY_COMPATIBLE environment variable"""
        with patch.dict("os.environ", {"TTY_COMPATIBLE": "0"}):
            assert is_color_compatible_terminal() is False
        
        with patch.dict("os.environ", {"TTY_COMPATIBLE": "1"}):
            assert is_color_compatible_terminal() is True

    def test_color_compatible_dumb_terminal(self):
        """Test that dumb terminals are detected as non-color compatible"""
        with patch.dict("os.environ", {"TERM": "dumb"}):
            assert is_color_compatible_terminal() is False
        
        with patch.dict("os.environ", {"TERM": "unknown"}):
            assert is_color_compatible_terminal() is False

    def test_color_compatible_stream_detection(self):
        """Test stream-based color compatibility detection"""
        # Mock stream with isatty
        mock_stream = Mock()
        mock_stream.isatty.return_value = True
        
        with patch.dict("os.environ", {}, clear=True):
            # Clear any environment variables that might affect the result
            for key in ["FORCE_COLOR", "NO_COLOR", "TTY_COMPATIBLE", "TERM"]:
                if key in os.environ:
                    del os.environ[key]
            
            # On Windows, need WT_SESSION or ANSICON for color support
            with patch("os.name", "posix"):  # Mock as non-Windows
                assert is_color_compatible_terminal(mock_stream) is True
        
        mock_stream.isatty.return_value = False
        assert is_color_compatible_terminal(mock_stream) is False

    def test_color_compatible_stream_no_isatty(self):
        """Test stream without isatty method"""
        mock_stream = Mock()
        del mock_stream.isatty  # Remove isatty method
        
        with patch.dict("os.environ", {}, clear=True):
            assert is_color_compatible_terminal(mock_stream) is False

    def test_color_compatible_stream_isatty_exception(self):
        """Test stream where isatty raises exception"""
        mock_stream = Mock()
        mock_stream.isatty.side_effect = OSError("I/O operation on closed file")
        
        with patch.dict("os.environ", {}, clear=True):
            assert is_color_compatible_terminal(mock_stream) is False

    def test_color_compatible_idle_detection(self):
        """Test that IDLE is detected as non-color compatible"""
        with patch("sys.stdin.__module__", "idlelib.pyshell"):
            assert is_color_compatible_terminal() is False



    def test_color_compatible_windows_detection(self):
        """Test Windows-specific color detection"""
        with patch("os.name", "nt"):
            # Without Windows Terminal or ANSICON
            with patch.dict("os.environ", {}, clear=True):
                assert is_color_compatible_terminal() is False
            
            # With Windows Terminal
            with patch.dict("os.environ", {"WT_SESSION": "1"}):
                mock_stream = Mock()
                mock_stream.isatty.return_value = True
                assert is_color_compatible_terminal(mock_stream) is True
            
            # With ANSICON
            with patch.dict("os.environ", {"ANSICON": "1"}):
                mock_stream = Mock()
                mock_stream.isatty.return_value = True
                assert is_color_compatible_terminal(mock_stream) is True

    def test_color_compatible_no_stream_provided(self):
        """Test color detection when no stream is provided"""
        with patch.dict("os.environ", {}, clear=True):
            # Clear any environment variables that might affect the result
            for key in ["FORCE_COLOR", "NO_COLOR", "TTY_COMPATIBLE", "TERM"]:
                if key in os.environ:
                    del os.environ[key]
            
            # On Windows, need WT_SESSION or ANSICON for color support
            with patch("os.name", "posix"):  # Mock as non-Windows
                assert is_color_compatible_terminal() is True