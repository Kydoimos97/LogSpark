"""Tests for is_color_compatible_terminal stream edge cases (lines 105-106)."""

from unittest.mock import Mock, patch

from logspark._Internal.Func.is_color_compatible_terminal import is_color_compatible_terminal


class TestColorCompatibilityStreamEdgeCases:
    """Test color compatibility stream edge cases."""

    def test_stream_isatty_exception_handling(self):
        """Test exception handling in stream isatty check (lines 105-106)."""
        mock_stream = Mock()
        mock_stream.isatty.side_effect = Exception("Mock isatty error")

        with patch.dict("os.environ", {}, clear=True):
            with patch("os.name", "posix"):
                result = is_color_compatible_terminal(stream=mock_stream)
        assert result is False

    def test_stream_no_isatty_method(self):
        """Test stream without isatty method (lines 105-106)."""
        mock_stream = Mock(spec=[])  # No isatty method

        with patch.dict("os.environ", {}, clear=True):
            with patch("os.name", "posix"):
                result = is_color_compatible_terminal(stream=mock_stream)
        assert result is False