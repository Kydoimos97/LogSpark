"""
Performance tests for LogSpark

These tests validate performance characteristics and detect regressions.
Tests focus on throughput, scaling, memory stability without correctness assertions.
"""

import gc
import logging
import os
import time
from io import StringIO

import pytest

from logspark.Handlers import SparkJsonHandler, SparkTerminalHandler
from logspark.Types.Options import TracebackOptions


def _debug_print(request, capsys, *args, **kwargs):
    """Print debug information only if capture is explicitly disabled"""
    if request.is_configured.getoption("capture") == "no":
        print(*args, **kwargs)


class TestDeepCallStackPerformance:
    """Test performance with deep call stacks and stacklevel handling"""

    def create_deep_call_stack(self, depth: int, target_logger):
        """Create a deep call stack and log from the bottom"""
        if depth <= 0:
            target_logger.info("Deep stack message")
            return
        self.create_deep_call_stack(depth - 1, target_logger)

    def test_deep_call_stack_performance(self, fresh_logger, request, capsys):
        """Test call-site resolution performance with deep call stacks"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)
            handler.setFormatter(
                logging.Formatter("%(name)s:%(filename)s:%(lineno)d - %(message)s")
            )

            fresh_logger.configure()
            fresh_logger.freeze()

            # Test with various call stack depths
            depths = [1, 5, 10, 20, 50]
            times = []

            for depth in depths:
                start_time = time.perf_counter()
                # Run multiple iterations for stable timing
                for _ in range(10):
                    self.create_deep_call_stack(depth, fresh_logger)
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                times.append(elapsed)

            # Performance validation: time should not grow exponentially with depth
            max_time = times[0] * 10  # Allow up to 10x growth from depth 1 to depth 50
            assert times[-1] <= max_time, f"Deep call stack performance degraded: {times}"

            _debug_print(
                request, capsys, f"Deep call stack times: {list(zip(depths, times, strict=False))}"
            )

    def test_fast_mode_performance_benefit(self, fresh_logger, request, capsys):
        """Test that LOGSPARK_MODE=fast provides performance benefit"""
        starting_val = os.environ.get("LOGSPARK_MODE", "")

        try:
            with StringIO() as devnull:
                handler = logging.StreamHandler(devnull)

                # Test with default mode (accurate call-site resolution)
                os.environ.pop("LOGSPARK_MODE", None)
                fresh_logger.configure()
                fresh_logger.freeze()

                start_time = time.perf_counter()
                for _i in range(1000):
                    self.create_deep_call_stack(10, fresh_logger)
                slow_time = time.perf_counter() - start_time

                # Reset logger for fast mode test
                fresh_logger._configured = None
                fresh_logger._frozen = False
                if fresh_logger._stdlib_logger:
                    fresh_logger._stdlib_logger.handlers.clear()

                # Test with fast mode (performance optimized)
                os.environ["LOGSPARK_MODE"] = "fast"
                fresh_logger.configure()
                fresh_logger.freeze()

                start_time = time.perf_counter()
                for _i in range(1000):
                    self.create_deep_call_stack(10, fresh_logger)
                fast_time = time.perf_counter() - start_time

                _debug_print(request, capsys, f"Default mode time: {slow_time:.4f}s")
                _debug_print(request, capsys, f"Fast mode time: {fast_time:.4f}s")
                _debug_print(request, capsys, f"Speedup: {slow_time / fast_time:.2f}x")

                # Fast mode should not be more than 20% slower (allows for measurement variance)
                assert fast_time <= slow_time * 1.2, (
                    f"Fast mode should not be slower: {fast_time} vs {slow_time}"
                )
        finally:
            if starting_val:
                os.environ["LOGSPARK_MODE"] = starting_val
            else:
                os.environ.pop("LOGSPARK_MODE", None)


class TestHighVolumeLoggingPerformance:
    """Test performance with high-volume logging"""

    def test_high_volume_logging_throughput(self, fresh_logger, request, capsys):
        """Test logging throughput with large numbers of calls"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

            fresh_logger.configure()
            fresh_logger.freeze()

            # Test with 10,000 log calls
            num_calls = 10000
            messages = [f"Message {i}" for i in range(num_calls)]

            start_time = time.perf_counter()
            for message in messages:
                fresh_logger.info(message)
            end_time = time.perf_counter()
            elapsed = end_time - start_time

            throughput = num_calls / elapsed
            _debug_print(
                request, capsys, f"High volume logging: {num_calls} calls in {elapsed:.4f}s"
            )
            _debug_print(request, capsys, f"Throughput: {throughput:.0f} calls/second")

            # Performance requirement: should handle at least 1000 calls/second
            assert throughput >= 1000, f"Throughput too low: {throughput:.0f} calls/second"

    @pytest.mark.silenced
    def test_level_filtering_performance(self, fresh_logger, request, capsys):
        """Test performance when many messages are filtered out by level"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            num_calls = 10000
            start_time = time.perf_counter()

            # Most of these should be filtered out
            for i in range(num_calls):
                fresh_logger.debug(f"Debug message {i}")  # Filtered
                fresh_logger.info(f"Info message {i}")  # Filtered
                fresh_logger.warning(f"Warning message {i}")  # Filtered
                if i % 100 == 0:  # Only 1% will be logged
                    fresh_logger.error(f"Error message {i}")  # Not filtered

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            total_calls = num_calls * 3 + (num_calls // 100)  # 3 filtered + some errors
            throughput = total_calls / elapsed

            _debug_print(request, capsys, f"Level filtering: {total_calls} calls in {elapsed:.4f}s")
            _debug_print(
                request, capsys, f"Throughput with filtering: {throughput:.0f} calls/second"
            )

            # Filtering should be very fast
            assert throughput >= 5000, (
                f"Filtering throughput too low: {throughput:.0f} calls/second"
            )

    @pytest.mark.silenced
    def test_pre_config_warning_performance(self, fresh_logger, request, capsys):
        """Test that pre-is_configured warnings don't significantly degrade performance"""
        num_calls = 1000
        start_time = time.perf_counter()

        # These should emit warnings but still be fast
        for i in range(num_calls):
            fresh_logger.info(f"Pre-is_configured message {i}")

        end_time = time.perf_counter()
        elapsed = end_time - start_time
        throughput = num_calls / elapsed

        _debug_print(request, capsys, f"Pre-is_configured logging: {num_calls} calls in {elapsed:.4f}s")
        _debug_print(request, capsys, f"Pre-is_configured throughput: {throughput:.0f} calls/second")

        # Should still be reasonably fast despite warnings
        assert throughput >= 500, f"Pre-is_configured throughput too low: {throughput:.0f} calls/second"


class TestLargePayloadPerformance:
    """Test performance with large message payloads"""

    def test_large_message_handling(self, fresh_logger, request, capsys):
        """Test logging performance with large messages"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            # Test with various message sizes
            sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

            for size in sizes:
                large_message = "A" * size
                start_time = time.perf_counter()
                fresh_logger.info(large_message)
                end_time = time.perf_counter()
                elapsed = end_time - start_time

                _debug_print(request, capsys, f"Large message ({size} bytes): {elapsed:.4f}s")

                # Should complete within reasonable time (1 second per MB)
                max_time = size / 1048576
                assert elapsed <= max_time, (
                    f"Large message ({size} bytes) took too long: {elapsed:.4f}s"
                )

    def test_structured_logging_performance(self, fresh_logger, request, capsys):
        """Test performance with structured data (dictionaries, objects)"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            # Create large structured data
            large_dict = {
                f"key_{i}": {
                    "nested_data": list(range(100)),
                    "metadata": {"timestamp": time.time(), "id": i},
                    "payload": "x" * 1000,
                }
                for i in range(100)
            }

            start_time = time.perf_counter()
            # Log structured data multiple times
            for i in range(10):
                fresh_logger.info(f"Structured data batch {i}: {large_dict}")
            end_time = time.perf_counter()
            elapsed = end_time - start_time

            _debug_print(request, capsys, f"Structured logging (10 large dicts): {elapsed:.4f}s")

            # Should complete within reasonable time
            assert elapsed <= 5.0, f"Structured logging took too long: {elapsed:.4f}s"


class TestJSONFormattingPerformance:
    """Test JSON formatting performance with traceback serialization"""

    def test_json_formatting_throughput(self, fresh_logger, request, capsys):
        """Test JSON formatting performance"""
        with StringIO() as devnull:
            json_handler = SparkJsonHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            num_calls = 1000
            start_time = time.perf_counter()

            for i in range(num_calls):
                fresh_logger.info(f"JSON message {i}")

            end_time = time.perf_counter()
            elapsed = end_time - start_time
            throughput = num_calls / elapsed

            _debug_print(request, capsys, f"JSON formatting: {num_calls} calls in {elapsed:.4f}s")
            _debug_print(request, capsys, f"JSON throughput: {throughput:.0f} calls/second")

            # JSON formatting should still be reasonably fast
            assert throughput >= 500, f"JSON throughput too low: {throughput:.0f} calls/second"

    def test_traceback_serialization_performance(self, fresh_logger, request, capsys):
        """Test performance of traceback serialization in JSON"""
        policies = [TracebackOptions.HIDE, TracebackOptions.COMPACT, TracebackOptions.FULL]

        for policy in policies:
            with StringIO() as devnull:
                json_handler = SparkJsonHandler(devnull)

                # Reset logger
                fresh_logger._configured = None
                fresh_logger._frozen = False
                if fresh_logger._stdlib_logger:
                    fresh_logger._stdlib_logger.handlers.clear()

                fresh_logger.configure()
                fresh_logger.freeze()

                num_exceptions = 100
                start_time = time.perf_counter()

                for i in range(num_exceptions):
                    try:
                        raise ValueError(f"Test exception {i}")
                    except ValueError:
                        fresh_logger.error(f"Exception occurred {i}", exc_info=True)

                end_time = time.perf_counter()
                elapsed = end_time - start_time
                throughput = num_exceptions / elapsed

                _debug_print(
                    request,
                    capsys,
                    f"Traceback serialization ({policy.value}): {num_exceptions} exceptions in {elapsed:.4f}s",
                )
                _debug_print(
                    request,
                    capsys,
                    f"Traceback throughput ({policy.value}): {throughput:.0f} exceptions/second",
                )

                # Should handle exceptions reasonably fast
                min_throughput = 50 if policy == TracebackOptions.FULL else 100
                assert throughput >= min_throughput, (
                    f"Traceback throughput too low ({policy.value}): {throughput:.0f}/s"
                )


class TestManagerUnificationPerformance:
    """Test logmanager unification performance"""

    def test_adopt_all_performance(self, fresh_log_manager, request, capsys):
        """Test adopt_all() performance with many loggers"""
        # Create many loggers in the registry
        num_loggers = 100
        test_loggers = []

        for i in range(num_loggers):
            logger_name = f"test.logger.{i}"
            test_logger = logging.getLogger(logger_name)
            test_loggers.append((logger_name, test_logger))

        # Measure adopt_all() performance
        start_time = time.perf_counter()
        fresh_log_manager.adopt_all()
        end_time = time.perf_counter()
        elapsed = end_time - start_time

        _debug_print(request, capsys, f"adopt_all() with {num_loggers} loggers: {elapsed:.4f}s")

        # Should complete quickly even with many loggers
        assert elapsed <= 1.0, f"adopt_all() took too long: {elapsed:.4f}s"

    def test_unify_format_performance(self, fresh_log_manager, fresh_logger, request, capsys):
        """Test unify_format() performance with many managed loggers"""
        # Create and adopt many loggers
        num_loggers = 50
        test_loggers = []

        for i in range(num_loggers):
            logger_name = f"unify.test.{i}"
            test_logger = logging.getLogger(logger_name)
            # Add some handlers to make unification more realistic
            test_logger.addHandler(logging.StreamHandler())
            test_loggers.append((logger_name, test_logger))

        fresh_log_manager.adopt_all()

        # Configure and freeze the main logger
        fresh_logger.configure()
        fresh_logger.freeze()

        # Measure unify_format() performance
        start_time = time.perf_counter()
        fresh_log_manager.unify(level=fresh_logger.instance.level, use_spark_handler=True)
        end_time = time.perf_counter()
        elapsed = end_time - start_time

        _debug_print(
            request, capsys, f"unify_format() with {num_loggers} managed loggers: {elapsed:.4f}s"
        )

        # Should complete quickly even with many loggers
        assert elapsed <= 2.0, f"unify_format() took too long: {elapsed:.4f}s"

    def test_scaling_behavior(self, fresh_log_manager, fresh_logger, request, capsys):
        """Test that manager operations scale reasonably with number of loggers"""
        logger_counts = [10, 25, 50, 100]
        adopt_times = []
        unify_times = []

        for count in logger_counts:
            # Clean up previous test loggers
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("scale.test."):
                    del logging.Logger.manager.loggerDict[logger_name]

            # Reset manager
            fresh_log_manager._state.managed_loggers.clear()
            fresh_log_manager._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

            # Create loggers for this test
            for i in range(count):
                logging.getLogger(f"scale.test.{i}")

            # Measure adopt_all time
            start_time = time.perf_counter()
            fresh_log_manager.adopt_all()
            adopt_time = time.perf_counter() - start_time
            adopt_times.append(adopt_time)

            # Configure and freeze logger for unify test
            fresh_logger._configured = None
            fresh_logger._frozen = False
            if fresh_logger._stdlib_logger:
                fresh_logger._stdlib_logger.handlers.clear()

            fresh_logger.configure()
            fresh_logger.freeze()

            # Measure unify_format time
            start_time = time.perf_counter()
            fresh_log_manager.unify(use_spark_handler=True)
            unify_time = time.perf_counter() - start_time
            unify_times.append(unify_time)

        _debug_print(request, capsys, "Scaling behavior:")
        _debug_print(request, capsys, f"Logger counts: {logger_counts}")
        _debug_print(request, capsys, f"adopt_all times: {adopt_times}")
        _debug_print(request, capsys, f"unify_format times: {unify_times}")

        # Times should not grow exponentially - allow linear growth but not worse than quadratic
        for i in range(1, len(logger_counts)):
            count_ratio = logger_counts[i] / logger_counts[0]
            adopt_ratio = adopt_times[i] / adopt_times[0]
            unify_ratio = unify_times[i] / unify_times[0]

            # Allow up to quadratic growth (count_ratio^2)
            max_growth = count_ratio**2

            assert adopt_ratio <= max_growth, (
                f"adopt_all() scaling too poor: {adopt_ratio} vs {max_growth}"
            )
            assert unify_ratio <= max_growth, (
                f"unify_format() scaling too poor: {unify_ratio} vs {max_growth}"
            )


class TestMemoryPerformance:
    """Test memory usage and garbage collection impact"""

    def test_memory_usage_stability(self, fresh_logger):
        """Test that logging does not leak memory - LogRecord objects should be garbage collected"""
        num_operations = 1000
        calls_per_iteration = 3

        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            # Force garbage collection and measure initial memory
            gc.collect()
            len(gc.get_objects())

            # Perform many logging operations
            for i in range(num_operations):
                fresh_logger.info(f"Memory test message {i}")
                fresh_logger.warning(f"Memory test warning {i}")
                fresh_logger.error(f"Memory test error {i}")

            # Force garbage collection and measure baseline
            gc.collect()
            baseline = len(gc.get_objects())

            for _ in range(calls_per_iteration):
                for _i in range(num_operations):
                    fresh_logger.info("msg")
                gc.collect()

            after = len(gc.get_objects())

            # LogRecord objects should be garbage collected after processing (no memory leaks)
            expected_growth = 0
            assert after - baseline == expected_growth

    def test_large_message_memory_efficiency(self, fresh_logger, request, capsys):
        """Test memory efficiency with large messages"""
        with StringIO() as devnull:
            handler = logging.StreamHandler(devnull)

            fresh_logger.configure()
            fresh_logger.freeze()

            # Create a large message
            large_message = "X" * 1048576  # 1MB message

            # Force garbage collection
            gc.collect()
            initial_objects = len(gc.get_objects())

            # Log the large message multiple times
            for i in range(10):
                fresh_logger.info(f"Large message {i}: {large_message}")

            # Force garbage collection
            gc.collect()
            final_objects = len(gc.get_objects())

            object_growth = final_objects - initial_objects

            _debug_print(
                request,
                capsys,
                f"Large message memory test: {initial_objects} -> {final_objects} objects ({object_growth:+d})",
            )

            # Should not accumulate objects from large messages
            assert object_growth <= 50, f"Large message memory leak: {object_growth} objects"
