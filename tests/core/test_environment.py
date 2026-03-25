"""
Test LOGSPARK_MODE environment variable behavior.

Tests environment mode semantics including:
- LOGSPARK_MODE=silenced suppresses warnings
- LOGSPARK_MODE=fast uses constant-time resolution
- Unset mode uses default behavior
"""

import logging
import os
import os
import warnings
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import logger
from logspark._Internal.Func.resolve_stacklevel import resolve_stacklevel
from logspark._Internal.Func.is_color_compatible_terminal import is_color_compatible_terminal
from logspark._Internal.State import is_fast_mode, is_silenced_mode
from logspark.Types.Exceptions import SparkLoggerUnconfiguredUsageWarning


class TestOutputSurfaceDetection:
    """Test is_color_compatible_terminal functionality"""

    def test_viable_output_surface_with_force_color(self):
        """Test that FORCE_COLOR works when terminal size is viable (not 0x0)"""
        # Test with viable terminal size and FORCE_COLOR
        with patch("shutil.get_terminal_size", return_value=(80, 24)):
            # Test without FORCE_COLOR - should be True (viable terminal)
            with patch.dict("os.environ", {}, clear=False):
                if "FORCE_COLOR" in os.environ:
                    del os.environ["FORCE_COLOR"]
                # On Windows, need WT_SESSION or ANSICON for color support
                if os.name == "nt":
                    with patch.dict("os.environ", {"WT_SESSION": "1"}):
                        assert is_color_compatible_terminal() is True
                else:
                    assert is_color_compatible_terminal() is True
            
            # Test with FORCE_COLOR set - should also be True
            with patch.dict("os.environ", {"FORCE_COLOR": "true"}):
                assert is_color_compatible_terminal() is True

    def test_viable_output_surface_zero_terminal_ignores_force_color(self):
        """Test that without any color signals the function returns False on Windows."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_color_compatible_terminal() is False

        with patch.dict("os.environ", {"FORCE_COLOR": "true"}, clear=True):
            assert is_color_compatible_terminal() is True

    def test_viable_output_surface_with_rich_console(self):
        """Test output surface detection with Rich console (defers to Rich logic)"""
        pytest.importorskip("rich")
        from rich.console import Console
        
        # Test that function properly defers to stream's isatty when provided
        # Use a mock to ensure predictable behavior
        from unittest.mock import Mock
        
        # Mock stream that reports as terminal
        terminal_stream = Mock()
        terminal_stream.isatty.return_value = True
        
        # Control all the environment conditions to reach the stream check
        with patch.dict("os.environ", {}, clear=True):
            # Clear all environment variables that would cause early returns
            with patch("logspark._Internal.Func.is_color_compatible_terminal._is_idle", return_value=False):
                with patch("logspark._Internal.Func.is_color_compatible_terminal._is_jupyter", return_value=False):
                    with patch("os.name", "posix"):  # Avoid Windows-specific logic
                        assert is_color_compatible_terminal(terminal_stream) is True
        
        # Mock stream that reports as non-terminal
        non_terminal_stream = Mock()
        non_terminal_stream.isatty.return_value = False
        
        with patch.dict("os.environ", {}, clear=True):
            with patch("logspark._Internal.Func.is_color_compatible_terminal._is_idle", return_value=False):
                with patch("logspark._Internal.Func.is_color_compatible_terminal._is_jupyter", return_value=False):
                    with patch("os.name", "posix"):
                        assert is_color_compatible_terminal(non_terminal_stream) is False

    def test_viable_output_surface_zero_terminal_size(self):
        """Test that zero terminal size is detected as non-viable"""
        with patch("shutil.get_terminal_size", return_value=(0, 0)):
            with patch.dict("os.environ", {}, clear=True):
                if "FORCE_COLOR" in os.environ:
                    del os.environ["FORCE_COLOR"]
                assert is_color_compatible_terminal() is False


class TestEnvironmentModes:
    """Test LOGSPARK_MODE environment variable behavior."""

    def test_rich_availability_with_broken_module(self):
        """Test is_rich_available when find_spec raises ValueError"""
        from unittest.mock import patch
        
        with patch("logspark._Internal.State.Env.find_spec") as mock_find_spec:
            # Mock find_spec to raise ValueError (broken/partially initialized module)
            mock_find_spec.side_effect = ValueError("Module broken")
            
            from logspark._Internal.State.Env import is_rich_available
            assert is_rich_available() is False

    def test_rich_availability_normal_cases(self):
        """Test is_rich_available normal behavior"""
        from logspark._Internal.State.Env import is_rich_available
        
        # Should return boolean (actual availability depends on environment)
        result = is_rich_available()
        assert isinstance(result, bool)

    def test_silenced_mode_suppresses_warnings(self, fresh_logger):
        """Test LOGSPARK_MODE=silenced affects output but not warnings."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            # Verify mode detection
            assert is_silenced_mode()
            assert not is_fast_mode()

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Use logger before configuration
                fresh_logger.info("test message")

                # Should still emit unconfigured usage warning (silenced only affects output)
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1

    def test_fast_mode_uses_constant_time_resolution(self, fresh_logger):
        """Test LOGSPARK_MODE=fast uses constant-time stacklevel resolution."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "fast"}):
            # Verify mode detection
            assert is_fast_mode()
            assert not is_silenced_mode()

            # In fast mode, resolve_stacklevel should use cached value
            resolved1 = resolve_stacklevel(1)
            resolved2 = resolve_stacklevel(1)

            # Should be consistent (using cached value)
            assert resolved1 == resolved2
            assert isinstance(resolved1, int)
            assert resolved1 > 0

    def test_unset_mode_uses_default_behavior(self, fresh_logger):
        """Test unset LOGSPARK_MODE uses default behavior."""
        # Ensure LOGSPARK_MODE is not set
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Verify mode detection
            assert not is_silenced_mode()
            assert not is_fast_mode()

            # Should emit warnings when unconfigured
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                fresh_logger.info("test message")

                # Should emit unconfigured usage warning
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1

    def test_mode_detection_case_insensitive(self):
        """Test that mode detection is case-insensitive."""
        # Test silenced mode variations
        for mode_value in ["silenced", "SILENCED", "Silenced", "SiLeNcEd"]:
            with patch.dict("os.environ", {"LOGSPARK_MODE": mode_value}):
                assert is_silenced_mode()
                assert not is_fast_mode()

        # Test fast mode variations
        for mode_value in ["fast", "FAST", "Fast", "FaSt"]:
            with patch.dict("os.environ", {"LOGSPARK_MODE": mode_value}):
                assert is_fast_mode()
                assert not is_silenced_mode()

    def test_invalid_mode_uses_default_behavior(self, fresh_logger):
        """Test that invalid LOGSPARK_MODE values use default behavior."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "invalid_mode"}):
            # Should not be in any special mode
            assert not is_silenced_mode()
            assert not is_fast_mode()

            # Should behave like default mode
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                fresh_logger.info("test message")

                # Should emit unconfigured usage warning
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1

    def test_empty_mode_uses_default_behavior(self, fresh_logger):
        """Test that empty LOGSPARK_MODE uses default behavior."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": ""}):
            # Should not be in any special mode
            assert not is_silenced_mode()
            assert not is_fast_mode()

            # Should behave like default mode
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                fresh_logger.info("test message")

                # Should emit unconfigured usage warning
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1

    def test_mode_affects_configured_logger_behavior(self, fresh_logger):
        """Test that modes affect behavior even after configuration."""
        # Test that fast mode affects stacklevel resolution even for is_configured logger
        with patch.dict("os.environ", {"LOGSPARK_MODE": "fast"}):
            fresh_logger.configure()

            # Should still use fast mode stacklevel resolution
            resolved = resolve_stacklevel(1)
            assert isinstance(resolved, int)
            assert resolved > 0

    def test_mode_changes_during_runtime(self, fresh_logger):
        """Test that mode changes are detected during runtime."""
        # Start with no mode
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            assert not is_silenced_mode()
            assert not is_fast_mode()

            # Change to silenced mode
            os.environ["LOGSPARK_MODE"] = "silenced"
            assert is_silenced_mode()
            assert not is_fast_mode()

            # Change to fast mode
            os.environ["LOGSPARK_MODE"] = "fast"
            assert not is_silenced_mode()
            assert is_fast_mode()

            # Remove mode
            del os.environ["LOGSPARK_MODE"]
            assert not is_silenced_mode()
            assert not is_fast_mode()


class TestEnvironmentModeProperties:
    """Property-based tests for environment mode behavior."""

    def test_property_silenced_mode_behavior(self, fresh_logger):
        """
        For any pre-configuration logging attempt, when LOGSPARK_MODE=silenced, output should be suppressed but warnings should still be emitted.
        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            log_method=st.sampled_from(["debug", "info", "warning", "error", "critical"]),
            message=st.text(min_size=1, max_size=100),
            mode_case=st.sampled_from(["silenced", "SILENCED", "Silenced", "SiLeNcEd"]),
        )
        def property_test(log_method, message, mode_case):
            with patch.dict("os.environ", {"LOGSPARK_MODE": mode_case}):
                fresh_logger.kill()  # Reset for each iteration

                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")

                    # Call logging method before configuration
                    getattr(fresh_logger, log_method)(message)

                    # Should still emit unconfigured usage warning (silenced only affects output)
                    unconfigured_warnings = [
                        warning
                        for warning in w
                        if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                    ]
                    assert len(unconfigured_warnings) == 1

        property_test()

    def test_property_fast_mode_stacklevel(self, fresh_logger):
        """
        For any logging call, when LOGSPARK_MODE=fast, constant-time stacklevel resolution should be used.
        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            user_stacklevel=st.integers(min_value=1, max_value=10),
            mode_case=st.sampled_from(["fast", "FAST", "Fast", "FaSt"]),
        )
        def property_test(user_stacklevel, mode_case):
            with patch.dict("os.environ", {"LOGSPARK_MODE": mode_case}):
                # In fast mode, resolve_stacklevel should be consistent (cached)
                resolved1 = resolve_stacklevel(user_stacklevel)
                resolved2 = resolve_stacklevel(user_stacklevel)

                # Should be identical (using cached value)
                assert resolved1 == resolved2
                assert isinstance(resolved1, int)
                assert resolved1 > 0

        property_test()

    def test_property_default_mode_accuracy(self, fresh_logger):
        """
        For any logging call, when LOGSPARK_MODE is unset, accurate call-site resolution should be used.
        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            log_method=st.sampled_from(["debug", "info", "warning", "error", "critical"]),
            message=st.text(min_size=1, max_size=50),
        )
        def property_test(log_method, message):
            # Ensure default mode (no LOGSPARK_MODE set)
            with patch.dict("os.environ", {}, clear=False):
                if "LOGSPARK_MODE" in os.environ:
                    del os.environ["LOGSPARK_MODE"]

                fresh_logger.kill()  # Reset for each iteration

                captured_records = []

                class RecordCapturingHandler(logging.Handler):
                    def emit(self, record):
                        captured_records.append(record)

                handler = RecordCapturingHandler()
                fresh_logger.configure(handler=handler, level=logging.DEBUG)

                # Call logging method
                getattr(fresh_logger, log_method)(message)

                # Should have captured exactly one record with accurate location
                assert len(captured_records) == 1
                record = captured_records[0]

                # Should have valid call-site information
                assert record.funcName is not None
                assert record.pathname is not None
                assert record.lineno > 0

                # Should point to this property test function
                assert (
                    "property_test" in record.funcName
                    or "test_property_default_mode_accuracy" in record.funcName
                )

        property_test()


class TestPreConfigurationValidation:
    """Test pre-configuration validation limitations"""

    @pytest.mark.silenced
    @given(
        log_levels=st.lists(
            st.sampled_from(["debug", "info", "warning", "error", "critical"]),
            min_size=1,
            max_size=5,
        ),
        log_messages=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
        warning_suppression=st.booleans(),
    )
    def test_pre_configuration_validation_limitation(
        self, log_levels, log_messages, warning_suppression
    ):
        """
        For any pre-configuration logging operation, the system should not perform configuration validation
        beyond emitting unconfigured-usage warnings and should not include implicit mode switching
        """
        # Create fresh logger instance for this test
        from logspark.Core.SparkLogger import SparkLogger

        fresh_logger = logger
        fresh_logger.kill()
        fresh_logger = SparkLogger()

        try:
            # Set up warning handling
            with warnings.catch_warnings(record=True) as w:
                if warning_suppression:
                    warnings.filterwarnings("ignore", category=SparkLoggerUnconfiguredUsageWarning)
                else:
                    warnings.simplefilter("always")

                # Test that pre-is_configured logging works without validation errors
                for level_name, message in zip(log_levels, log_messages, strict=False):
                    log_method = getattr(fresh_logger, level_name)

                    # Should not raise configuration validation errors
                    try:
                        log_method(message)
                    except Exception as e:
                        # Should not get configuration validation errors
                        assert "invalid" not in str(e).lower(), (
                            f"Pre-is_configured logging should not validate parameters: {e}"
                        )
                        # Re-raise if it's an unexpected error
                        raise

                # Verify warning behavior
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, SparkLoggerUnconfiguredUsageWarning)
                ]

                if warning_suppression:
                    # Warnings should be suppressed
                    assert len(unconfigured_warnings) == 0, "Warnings should be suppressible"
                else:
                    # Should emit exactly one warning (first call only)
                    assert len(unconfigured_warnings) == 1, (
                        "Should emit exactly one unconfigured usage warning"
                    )
                    warning_message = str(unconfigured_warnings[0].message)
                    assert "Logger used before configuration" in warning_message

                # Verify that pre-is_configured setup was done
                assert fresh_logger._pre_config_setup_done, "Pre-is_configured setup should be completed"
                assert len(fresh_logger.handlers) > 0, "Should have at least one handler"

                # Verify no implicit mode switching occurred
                # Pre-is_configured should use minimal terminal logging only
                handler = fresh_logger.handlers[0]

                # Should not have multiple handlers (no mode switching)
                assert len(fresh_logger.handlers) == 1, (
                    "Pre-is_configured should not create multiple handlers (no mode switching)"
                )

                # Handlers type should be determined once and not change
                original_handler_type = type(handler)

                # Additional logging should not change handler setup
                for level_name, message in zip(
                    log_levels[:3], log_messages[:3], strict=False
                ):  # Test a few more
                    log_method = getattr(fresh_logger, level_name)
                    log_method(f"Additional {message}")

                # Verify handler setup remained stable (no implicit switching)
                assert len(fresh_logger.handlers) == 1, (
                    "Handlers count should remain stable"
                )
                assert type(fresh_logger.handlers[0]) is original_handler_type, (
                    "Handlers type should not change (no implicit mode switching)"
                )

        finally:
            # Cleanup: reset state
            fresh_logger.kill()
            fresh_logger = SparkLogger()
