# tests/test_validate_level.py

import logging
from enum import IntEnum

import pytest

from logspark._Internal.Func import validate_level

# ─────────────────────────────────────────────────────────────
# Test setup: register custom logging levels
# ─────────────────────────────────────────────────────────────

TRACE_LEVEL = 5


@pytest.fixture(scope="module", autouse=True)
def register_custom_levels():
    if TRACE_LEVEL not in logging._levelToName:
        logging.addLevelName(TRACE_LEVEL, "TRACE")
    yield


# ─────────────────────────────────────────────────────────────
# Integer levels
# ─────────────────────────────────────────────────────────────


def test_int_levels_valid():
    levels = [
        logging.NOTSET,  # 0
        TRACE_LEVEL,  # 5
        logging.DEBUG,  # 10
        logging.INFO,  # 20
        logging.WARNING,  # 30
        logging.ERROR,  # 40
        logging.CRITICAL,  # 50
    ]

    for level in levels:
        assert validate_level(level) == level


def test_int_levels_invalid():
    levels = [-1, 7, 15, 60, 999]

    for level in levels:
        with pytest.raises(KeyError):
            validate_level(level)


# ─────────────────────────────────────────────────────────────
# Enum levels
# ─────────────────────────────────────────────────────────────


def test_enum_levels_valid():
    class TestEnum(IntEnum):
        TRACE = TRACE_LEVEL
        DEBUG = logging.DEBUG
        INFO = logging.INFO

    for level in TestEnum:
        assert validate_level(level) == int(level)


# ─────────────────────────────────────────────────────────────
# String levels
# ─────────────────────────────────────────────────────────────


def test_string_levels_valid():
    levels = [
        "NOTSET",
        "TRACE",
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
        "WARN",
        "FATAL",
    ]

    for level in levels:
        result = validate_level(level)
        assert isinstance(result, int)


def test_string_levels_invalid():
    levels = [
        "debug",
        "Info",
        "TRACE ",
        " VERBOSE",
        "",
    ]

    for level in levels:
        with pytest.raises(KeyError):
            validate_level(level)


# ─────────────────────────────────────────────────────────────
# Custom levels
# ─────────────────────────────────────────────────────────────


def test_custom_levels_valid():
    assert validate_level("TRACE") == TRACE_LEVEL
    assert validate_level(TRACE_LEVEL) == TRACE_LEVEL


# ─────────────────────────────────────────────────────────────
# Invalid types
# ─────────────────────────────────────────────────────────────


def test_invalid_level_types():
    levels = [None, 1.5, object(), [], {}]

    for level in levels:
        with pytest.raises(TypeError):
            validate_level(level)
