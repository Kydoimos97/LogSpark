"""Tests for DDTrace filter handling in SparkLoggerDef (lines 291-292)."""

import logging
from unittest.mock import patch

from logspark.Filters.DDTraceInjectionFilter import DDTraceInjectionFilter


class TestDDTraceFilterHandling:
    """Test DDTrace filter handling in configure method."""

    def test_ddtrace_filter_added_when_missing(self, fresh_logger):
        """Test that DDTrace filter is added when not present (lines 291-292)."""
        with patch("logspark.Core.SparkLogger.is_ddtrace_available", return_value=True):
            fresh_logger.configure()

            ddtrace_filters = [
                f for f in fresh_logger.filters
                if isinstance(f, DDTraceInjectionFilter)
            ]
            assert len(ddtrace_filters) == 1

    def test_ddtrace_filter_not_duplicated_when_present(self, fresh_logger):
        """Test that DDTrace filter is not duplicated when already present."""
        with patch("logspark.Core.SparkLogger.is_ddtrace_available", return_value=True):
            existing_filter = DDTraceInjectionFilter()
            fresh_logger.addFilter(existing_filter)

            initial_ddtrace_filters = [
                f for f in fresh_logger.filters
                if isinstance(f, DDTraceInjectionFilter)
            ]
            assert len(initial_ddtrace_filters) == 1
            assert initial_ddtrace_filters[0] is existing_filter

            fresh_logger.configure()

            final_ddtrace_filters = [
                f for f in fresh_logger.filters
                if isinstance(f, DDTraceInjectionFilter)
            ]
            assert len(final_ddtrace_filters) == 1
            assert final_ddtrace_filters[0] is existing_filter

    def test_ddtrace_filter_preserved_across_reconfigurations(self, fresh_logger):
        """Test that DDTrace filter instance is preserved across reconfiguration.

        _apply_config clears handlers but not filters. Using no_freeze=True allows
        reconfiguration while keeping existing filters intact.
        """
        with patch("logspark.Core.SparkLogger.is_ddtrace_available", return_value=True):
            fresh_logger.configure(no_freeze=True)

            original_ddtrace_filters = [
                f for f in fresh_logger.filters
                if isinstance(f, DDTraceInjectionFilter)
            ]
            assert len(original_ddtrace_filters) == 1
            original_filter = original_ddtrace_filters[0]

            fresh_logger.configure(no_freeze=True)

            new_ddtrace_filters = [
                f for f in fresh_logger.filters
                if isinstance(f, DDTraceInjectionFilter)
            ]
            assert len(new_ddtrace_filters) == 1
            assert new_ddtrace_filters[0] is original_filter
