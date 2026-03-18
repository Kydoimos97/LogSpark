"""Tests for DDTrace filter handling in SparkLoggerDef (lines 291-292)."""

import logging

from logspark.Filters.DDTraceInjectionFilter import DDTraceInjectionFilter


class TestDDTraceFilterHandling:
    """Test DDTrace filter handling in configure method."""

    def test_ddtrace_filter_added_when_missing(self, fresh_logger):
        """Test that DDTrace filter is added when not present (lines 291-292)."""
        # Configure logger without any existing filters
        fresh_logger.configure()
        
        # Should have DDTrace filter
        ddtrace_filters = [
            f for f in fresh_logger.instance.filters 
            if isinstance(f, DDTraceInjectionFilter)
        ]
        assert len(ddtrace_filters) == 1

    def test_ddtrace_filter_not_duplicated_when_present(self, fresh_logger):
        """Test that DDTrace filter is not duplicated when already present."""
        # Manually add DDTrace filter first
        existing_filter = DDTraceInjectionFilter()
        fresh_logger.instance.addFilter()
        
        # Should have exactly one DDTrace filter
        initial_ddtrace_filters = [
            f for f in fresh_logger.instance.filters 
            if isinstance(f, DDTraceInjectionFilter)
        ]
        assert len(initial_ddtrace_filters) == 1
        assert initial_ddtrace_filters[0] is existing_filter
        
        # Configure logger
        fresh_logger.configure()
        
        # Should still have only one DDTrace filter (no duplicates)
        final_ddtrace_filters = [
            f for f in fresh_logger.instance.filters 
            if isinstance(f, DDTraceInjectionFilter)
        ]
        assert len(final_ddtrace_filters) == 1
        assert final_ddtrace_filters[0] is existing_filter  # Same instance preserved

    def test_ddtrace_filter_preserved_across_reconfigurations(self, fresh_logger):
        """Test that DDTrace filter is preserved when reconfiguring."""
        # First configuration
        fresh_logger.configure()
        
        # Get the DDTrace filter
        original_ddtrace_filters = [
            f for f in fresh_logger.instance.filters 
            if isinstance(f, DDTraceInjectionFilter)
        ]
        assert len(original_ddtrace_filters) == 1
        original_filter = original_ddtrace_filters[0]
        
        # Reconfigure
        fresh_logger.configure()
        
        # Should still have the same DDTrace filter
        new_ddtrace_filters = [
            f for f in fresh_logger.instance.filters 
            if isinstance(f, DDTraceInjectionFilter)
        ]
        assert len(new_ddtrace_filters) == 1
        assert new_ddtrace_filters[0] is original_filter  # Same instance preserved