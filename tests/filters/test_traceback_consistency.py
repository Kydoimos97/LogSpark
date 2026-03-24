"""
Test that handlers emit exception records consistently.

This module verifies that SparkTerminalHandler, SparkJsonHandler, and
SparkPreConfigHandler all handle exception records without error under
various traceback policies.
"""

import io
import logging
import sys

import pytest

from logspark.Filters.TracebackPolicyFilter import TracebackPolicyFilter
from logspark.Types.Options import TracebackOptions


def _make_exception_record():
    try:
        raise ValueError("Consistency test exception")
    except ValueError:
        return logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=sys.exc_info(),
        )


def _apply_filter(record):
    """Run TracebackPolicyFilter on a record in place."""
    TracebackPolicyFilter().filter(record)
    return record


class TestHandlerEmitConsistency:
    """Test that all handlers emit without error on exception records."""

    def test_terminal_handler_emits_with_compact_policy(self):
        """Test SparkTerminalHandler emits exception records under COMPACT policy."""
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        stream = io.StringIO()
        handler = SparkTerminalHandler(stream=stream, traceback_policy=TracebackOptions.COMPACT)
        record = _apply_filter(_make_exception_record())
        handler.emit(record)
        assert len(stream.getvalue()) > 0

    def test_terminal_handler_emits_with_full_policy(self):
        """Test SparkTerminalHandler emits exception records under FULL policy."""
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        stream = io.StringIO()
        handler = SparkTerminalHandler(stream=stream, traceback_policy=TracebackOptions.FULL)
        record = _apply_filter(_make_exception_record())
        handler.emit(record)
        assert len(stream.getvalue()) > 0

    def test_terminal_handler_emits_with_hide_policy(self):
        """Test SparkTerminalHandler emits exception records under HIDE policy."""
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        stream = io.StringIO()
        handler = SparkTerminalHandler(stream=stream, traceback_policy=TracebackOptions.HIDE)
        record = _apply_filter(_make_exception_record())
        handler.emit(record)
        assert len(stream.getvalue()) > 0

    def test_json_handler_emits_with_exception(self):
        """Test SparkJsonHandler emits exception records without error."""
        pytest.importorskip("pythonjsonlogger")
        from logspark.Handlers.SparkJsonHandler import SparkJsonHandler

        stream = io.StringIO()
        handler = SparkJsonHandler(stream=stream)
        record = _apply_filter(_make_exception_record())
        handler.emit(record)
        assert len(stream.getvalue()) > 0

    def test_terminal_and_json_both_emit_on_same_exception(self):
        """Test terminal and JSON handlers both emit the same exception record."""
        pytest.importorskip("pythonjsonlogger")
        from logspark.Handlers.SparkJsonHandler import SparkJsonHandler
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(
            stream=terminal_stream, traceback_policy=TracebackOptions.COMPACT
        )
        json_stream = io.StringIO()
        json_handler = SparkJsonHandler(stream=json_stream)

        terminal_record = _apply_filter(_make_exception_record())
        json_record = _apply_filter(_make_exception_record())

        terminal_handler.emit(terminal_record)
        json_handler.emit(json_record)

        assert len(terminal_stream.getvalue()) > 0
        assert len(json_stream.getvalue()) > 0
