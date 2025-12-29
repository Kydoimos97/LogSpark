"""
Integration tests for LogSpark Logging

These tests verify that the main import interface works correctly.
"""

import logging
import warnings
import pytest
from io import StringIO


class TestMainImportInterface:
    """Test the main import interface from logspark"""

    def test_main_import_works(self):
        """Test that main import from logspark works"""
        from logspark import logger, spark_log_manager

        assert logger is not None
        assert spark_log_manager is not None
        assert hasattr(logger, "configure")
        assert hasattr(spark_log_manager, "adopt_all")
        assert hasattr(spark_log_manager, "unify_format")

    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        from logspark import logger, spark_log_manager

        # Create a test stream to capture output
        test_stream = StringIO()
        handler = logging.StreamHandler(test_stream)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)

        # Configure logger (automatically frozen)
        logger.configure(level=logging.INFO, handler=handler)
        # Use logger
        logger.info("Test message")

        # Verify output
        output = test_stream.getvalue()
        assert "INFO: Test message" in output

        # Test logmanager
        spark_log_manager.adopt_all()
        managed_logger = spark_log_manager.managed("LogSpark")
        assert isinstance(managed_logger, logging.Logger)

        # Test global unification
        spark_log_manager.unify_format()  # Should not raise

    @pytest.mark.silenced
    def test_pre_config_usage_workflow(self, fresh_logger):
        """Test pre-configuration usage workflow"""
        # Reset singleton to get truly fresh logger
        from logspark import logger

        # Reset the singleton instance
        if hasattr(logger, "_SingletonWrapper__cls_instance"):
            logger._SingletonWrapper__cls_instance = None

        fresh_logger = logger

        # Use logger before configuration (should emit warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fresh_logger.info("Pre-config message")

            assert len(w) == 1
            assert "Logger used before explicit configuration" in str(w[0].message)

        # Should still work after configuration
        test_stream = StringIO()
        handler = logging.StreamHandler(test_stream)
        fresh_logger.configure(handler=handler)

        fresh_logger.info("Post-config message")
        output = test_stream.getvalue()
        assert "Post-config message" in output
