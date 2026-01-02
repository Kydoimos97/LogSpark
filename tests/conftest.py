"""
Pytest configuration and fixtures for LogSpark test suite refactor.
Provides behavioral test infrastructure with dependency guards and environment isolation.
"""

import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import Verbosity, settings

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Hypothesis configuration for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.load_profile("default")


# Dependency Guard Fixtures
@pytest.fixture
def require_rich():
    """Skip test if Rich is not available"""
    pytest.importorskip("rich")


@pytest.fixture
def require_ddtrace():
    """Skip test if DDTrace is not available"""
    pytest.importorskip("ddtrace")


@pytest.fixture
def require_json_logger():
    """Skip test if python-json-logger is not available"""
    pytest.importorskip("pythonjsonlogger")


# Environment Isolation Fixtures
@pytest.fixture
def isolated_environment():
    """Provide clean environment for each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def silenced_mode():
    """Set LOGSPARK_MODE=silenced for test"""
    with patch.dict(os.environ, {"LOGSPARK_MODE": "silenced"}):
        yield


@pytest.fixture
def fast_mode():
    """Set LOGSPARK_MODE=fast for test"""
    with patch.dict(os.environ, {"LOGSPARK_MODE": "fast"}):
        yield


@pytest.fixture
def default_mode():
    """Ensure LOGSPARK_MODE is unset for default behavior"""
    with patch.dict(os.environ, {}, clear=False):
        if "LOGSPARK_MODE" in os.environ:
            del os.environ["LOGSPARK_MODE"]
        yield


# Fresh Instance Management Fixtures
@pytest.fixture
def fresh_logger():
    """Provide fresh logger instance with proper cleanup"""
    from logspark import logger

    logger.kill()  # Reset to clean state
    yield logger
    logger.kill()  # Cleanup


@pytest.fixture
def fresh_log_manager():
    """Provide fresh log manager with proper cleanup"""
    from logspark import spark_log_manager

    spark_log_manager.release_all()
    # Clear the LogSpark logger that gets auto-added by release_all()
    with spark_log_manager._lock:
        spark_log_manager._state.managed_loggers.clear()
    yield spark_log_manager
    spark_log_manager.release_all()


# Test Infrastructure Fixtures
@pytest.fixture
def test_stream():
    """Provide StringIO stream for capturing log output"""
    return io.StringIO()


@pytest.fixture
def test_handler(test_stream):
    """Provide test StreamHandler for configuration"""
    import logging

    handler = logging.StreamHandler(test_stream)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    return handler


@pytest.fixture
def configured_logger(fresh_logger, test_handler):
    """Provide configured but not frozen logger"""
    import logging

    from logspark.Types import TracebackOptions

    fresh_logger.configure(
        level=logging.INFO, traceback=TracebackOptions.NONE, handler=test_handler
    )
    return fresh_logger


@pytest.fixture
def frozen_logger(configured_logger):
    """Provide configured and frozen logger"""
    return configured_logger


# Legacy compatibility fixture for existing tests
@pytest.fixture(autouse=True)
def logspark_mode(request):
    """Legacy fixture for backward compatibility with existing tests"""
    marker = request.node.get_closest_marker("silenced")

    if marker:
        os.environ["LOGSPARK_MODE"] = "silenced"
    else:
        os.environ.pop("LOGSPARK_MODE", None)

    yield

    os.environ.pop("LOGSPARK_MODE", None)


# Collection-time dependency handling
def pytest_ignore_collect(path, config):
    """Skip collection of tests that require unavailable dependencies"""
    try:
        from pathlib import Path

        p = Path(path)
    except TypeError:
        # fallback for py.path.local
        p = Path(str(path))

    # Skip rich directory if Rich is not available
    if p.is_dir() and p.name == "rich":
        try:
            import rich  # noqa: F401
        except ImportError:
            return True

    return False
