"""Tests for PathNormalizationFilter edge cases."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from logspark.Filters.PathNormalizationFilter import PathNormalizationFilter
from logspark.Types.Options import PathResolutionSetting


class TestPathNormalizationFilterProjectRoot:

    def test_project_root_falls_back_to_file_when_unresolvable(self):
        """When resolve_project_root() returns None, mode degrades to FILE."""
        f = PathNormalizationFilter(resolution_mode=PathResolutionSetting.RELATIVE)
        with patch(
            "logspark.Filters.PathNormalizationFilter.resolve_project_root",
            return_value=None,
        ):
            root = f.project_root
        assert root is None
        assert f.resolution_mode == PathResolutionSetting.FILE

    def test_project_root_setter_stores_value(self):
        """The project_root setter writes directly to _project_root."""
        f = PathNormalizationFilter()
        custom = Path("/custom/project")
        f.project_root = custom
        assert f._project_root == custom

    def test_project_root_setter_accepts_none(self):
        """Setting project_root to None clears the cached value."""
        f = PathNormalizationFilter()
        f.project_root = Path("/some/path")
        f.project_root = None
        assert f._project_root is None
