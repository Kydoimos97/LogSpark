"""Tests for SparkFilterModule base class."""

import logging
from typing import Any

import pytest

from logspark._Internal.SparkLogFilter import SparkFilterModule


class _ConcreteFilter(SparkFilterModule):
    """Minimal concrete subclass for testing the abstract base."""

    def configure(self, **kwargs: Any) -> None: ...

    def filter(self, record: logging.LogRecord) -> bool:
        return True


class TestSparkFilterModule:

    def test_auto_name_from_class_when_no_name_given(self):
        """When instantiated without a name the class name is used."""
        f = _ConcreteFilter()
        assert f.name == "_ConcreteFilter"

    def test_explicit_name_is_preserved(self):
        """An explicit name is kept as-is."""
        f = _ConcreteFilter(name="my.filter")
        assert f.name == "my.filter"

    def test_inject_defaults_to_false(self):
        f = _ConcreteFilter()
        assert f.inject is False

    def test_set_injection_true(self):
        f = _ConcreteFilter()
        f.set_injection(True)
        assert f.inject is True

    def test_set_injection_false(self):
        f = _ConcreteFilter()
        f.set_injection(True)
        f.set_injection(False)
        assert f.inject is False
