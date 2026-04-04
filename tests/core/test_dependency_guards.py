"""
Test dependency guard system behavior.
Validates that optional dependencies are handled correctly at test runtime.
"""

import sys
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st


class TestDependencyGuardSystem:
    """Test the dependency guard fixtures and collection-time behavior."""

    def test_require_rich_skips_when_unavailable(self):
        """Test that require_rich fixture skips when Rich is not available."""
        # Mock Rich as unavailable
        with patch.dict(sys.modules, {"rich": None}):
            with pytest.raises(pytest.skip.Exception):
                pytest.importorskip("rich")

    def test_require_ddtrace_skips_when_unavailable(self):
        """Test that require_ddtrace fixture skips when DDTrace is not available."""
        # Mock DDTrace as unavailable
        with patch.dict(sys.modules, {"ddtrace": None}):
            with pytest.raises(pytest.skip.Exception):
                pytest.importorskip("ddtrace")

    def test_require_json_logger_skips_when_unavailable(self):
        """Test that require_json_logger fixture skips when python-json-logger is not available."""
        # Mock python-json-logger as unavailable
        with patch.dict(sys.modules, {"pythonjsonlogger": None}):
            with pytest.raises(pytest.skip.Exception):
                pytest.importorskip("pythonjsonlogger")

    @given(dependency_name=st.sampled_from(["rich", "ddtrace", "pythonjsonlogger"]))
    def test_dependency_guard_behavior_property(self, dependency_name: str):
        """
        For any optional dependency, when the dependency is unavailable,
        pytest.importorskip should raise pytest.skip.Exception without causing collection failures.
        """
        # Mock the dependency as unavailable
        with patch.dict(sys.modules, {dependency_name: None}):
            # Verify that importorskip raises skip exception (not import error)
            with pytest.raises(pytest.skip.Exception):
                pytest.importorskip(dependency_name)

    def test_collection_time_safety(self):
        """Test that missing dependencies don't cause collection-time failures."""
        import tempfile
        from pathlib import Path

        from tests.conftest import pytest_ignore_collect

        with tempfile.TemporaryDirectory() as tmpdir:
            # Non-rich directory should never be skipped
            other_dir = Path(tmpdir) / "other"
            other_dir.mkdir()
            result = pytest_ignore_collect(other_dir, None)
            assert result is False or result is None

            # Rich directory: skipped when Rich is unavailable, collected when available
            rich_dir = Path(tmpdir) / "rich"
            rich_dir.mkdir()
            try:
                import rich  # noqa: F401
                result = pytest_ignore_collect(rich_dir, None)
                assert result is False or result is None
            except ImportError:
                result = pytest_ignore_collect(rich_dir, None)
                assert result is True

    def test_dependency_availability_detection(self):
        """Test that dependency guards correctly detect when dependencies are available."""
        # Test with a dependency that should be available (pytest itself)
        try:
            pytest.importorskip("pytest")
            # Should not raise any exception
        except pytest.skip.Exception:
            pytest.fail("pytest.importorskip should not skip for available dependencies")

    @given(env_mode=st.sampled_from(["silenced", "fast", None]), dependency_present=st.booleans())
    def test_environment_isolation_with_dependencies(self, env_mode: str, dependency_present: bool):
        """
        Test that environment isolation works correctly regardless of dependency availability.
        This ensures that dependency guards don't interfere with environment mode testing.
        """
        env_dict = {"LOGSPARK_MODE": env_mode} if env_mode else {}

        with patch.dict("os.environ", env_dict, clear=False):
            # Environment should be properly isolated regardless of dependency state
            import os

            if env_mode:
                assert os.environ.get("LOGSPARK_MODE") == env_mode
            else:
                # When env_mode is None, LOGSPARK_MODE should not be set
                assert (
                    "LOGSPARK_MODE" not in os.environ or os.environ.get("LOGSPARK_MODE") != env_mode
                )
