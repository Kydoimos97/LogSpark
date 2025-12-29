"""
Basic setup tests for LogSpark Logging

These tests verify that the basic structure and imports work correctly.
"""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import spark_log_manager, logger
from logspark.Types.Exceptions import (
    FrozenConfigurationError,
    InvalidConfigurationError,
    LogSparkError,
    UnconfiguredUsageWarning,
    UnfrozenGlobalOperationError
)
from logspark.Internal.State import LoggerConfig
from logspark.Types import TracebackOptions

class TestBasicImports:
    """Test that all expected components can be imported"""

    def test_logger_import(self):
        """Test that logger singleton can be imported"""
        assert logger is not None
        assert hasattr(logger, "configure")
        assert hasattr(logger, "freeze")
        assert hasattr(logger, "is_frozen")

    def test_log_manager_import(self):
        """Test that logmanager singleton can be imported"""
        assert spark_log_manager is not None
        assert hasattr(spark_log_manager, "adopt_all")
        assert hasattr(spark_log_manager, "managed")
        assert hasattr(spark_log_manager, "unify_format")

    def test_models_import(self):
        """Test that data models can be imported"""
        assert LoggerConfig is not None
        assert TracebackOptions is not None

    def test_exceptions_import(self):
        """Test that exception classes can be imported"""
        assert LogSparkError is not None
        assert FrozenConfigurationError is not None
        assert UnfrozenGlobalOperationError is not None
        assert InvalidConfigurationError is not None
        assert UnconfiguredUsageWarning is not None


class TestTracebackPolicy:
    """Test TracebackOptions enum"""

    def test_traceback_policy_values(self):
        """Test that TracebackOptions has expected values"""
        assert TracebackOptions.NONE.value is None
        assert TracebackOptions.COMPACT.value == "compact"
        assert TracebackOptions.FULL.value == "full"


class TestLoggerConfig:
    """Test LoggerConfig data model"""

    def test_logger_config_creation(self):
        """Test that LoggerConfig can be created with valid parameters"""
        handler = logging.StreamHandler()
        config = LoggerConfig(
            level=logging.INFO,
            handler=handler,
            traceback_policy=TracebackOptions.NONE,
        )

        assert config.level == logging.INFO
        assert config.handler is handler
        assert config.traceback_policy == TracebackOptions.NONE

    def test_logger_config_validation(self):
        """Test that LoggerConfig validates parameters"""
        handler = logging.StreamHandler()

        # Test invalid level
        with pytest.raises(ValueError):
            LoggerConfig(
                level="invalid",
                handler=handler,
                traceback_policy=TracebackOptions.NONE,
            )

        # Test invalid handler
        with pytest.raises(ValueError):
            LoggerConfig(
                level=logging.INFO,
                handler="invalid",
                traceback_policy=TracebackOptions.NONE,
            )

        # Test invalid traceback_policy
        with pytest.raises(ValueError):
            LoggerConfig(
                level=logging.INFO, handler=handler, traceback_policy="invalid"
            )


class TestBasicFunctionality:
    """Test basic functionality works"""

    def test_logger_singleton_identity(self):
        """Test that logger maintains singleton identity"""
        from logspark import logger
        
        # Test that multiple imports return the same singleton
        logger2 = logger
        assert logger is logger2

    def test_log_manager_singleton_identity(self):
        """Test that logmanager maintains singleton identity"""
        from logspark import spark_log_manager
        
        # Test that multiple imports return the same singleton
        logmanager2 = spark_log_manager
        assert logmanager2 is spark_log_manager

    @given(st.text())
    def test_logger_basic_logging_methods_exist(self, message):
        """Property test: Logger has all expected logging methods"""
        # This is a basic property test to verify the setup
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")

        # Test that methods are callable (don't actually call them to avoid side effects)
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)
        assert callable(logger.critical)
