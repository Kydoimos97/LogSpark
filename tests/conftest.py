"""
Pytest configuration and fixtures for LogSpark Logging v2 tests
"""
import io
import os
import sys
from io import StringIO
from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from logspark.Types import TracebackOptions
import logging

from pathlib import Path

def pytest_ignore_collect(path, config):
    try:
        from pathlib import Path
        p = Path(path)
    except TypeError:
        # fallback for py.path.local
        p = Path(str(path))

    if p.is_dir() and p.name == "rich":
        try:
            import rich  # noqa: F401
        except Exception:
            return True

    return False

@pytest.fixture(autouse=True)
def logspark_mode(request):
    marker = request.node.get_closest_marker("silenced")

    if marker:
        os.environ["LOGSPARK_MODE"] = "silenced"
    else:
        os.environ.pop("LOGSPARK_MODE", None)

    yield

    os.environ.pop("LOGSPARK_MODE", None)

@pytest.fixture
def fresh_logger():
    """Provide a fresh logger instance for testing"""
    from logspark import logger
    
    # Use the new kill() method to properly reset the logger
    logger.kill()
    
    yield logger
    
    # Cleanup using kill() method
    logger.kill()


@pytest.fixture
def fresh_log_manager():
    """Provide a fresh logmanager instance for testing"""
    from logspark import spark_log_manager

    # Use the new release() method to properly reset the log manager
    spark_log_manager.release()

    yield spark_log_manager

    # Cleanup using release() method
    spark_log_manager.release()


@pytest.fixture
def test_stream():
    """Provide a devnull stream for capturing log output"""
    # with StringIO() as stream:
    #     yield stream
    stream = io.StringIO()
    yield stream

@pytest.fixture
def test_handler(test_stream):
    """Provide a test StreamHandler for configuration"""
    handler = logging.StreamHandler(test_stream)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    return handler


@pytest.fixture
def configured_logger(fresh_logger, test_handler):
    """Provide a configured but not frozen logger"""
    fresh_logger.configure(level=logging.INFO, fast_log=False, traceback=TracebackOptions.NONE, handler=test_handler)
    return fresh_logger


@pytest.fixture
def frozen_logger(configured_logger):
    """Provide a configured and frozen logger"""
    return configured_logger


# Hypothesis configuration
from hypothesis import Verbosity, settings

# Configure hypothesis for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.load_profile("default")
