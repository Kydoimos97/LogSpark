import logging
from logging import LogRecord
from pathlib import Path
from typing import cast

from .._Internal.State import resolve_project_root
from ..Types.Options import PathResolutionSetting
from ..Types.SparkRecordAttrs import (
    HasSparkAttributes,
    SparkRecordAttrs,
    has_spark_extra_attributes,
)


class PathNormalizationFilter(logging.Filter):
    """
    Filter that resolves and normalises source file paths on each log record.

    Populates ``record.spark.filepath``, ``record.spark.filename``,
    ``record.spark.uri``, and related fields according to ``resolution_mode``:

    - ``RELATIVE`` — path relative to the detected project root (falls back to
      ``FILE`` mode when the root cannot be resolved)
    - ``ABSOLUTE`` — absolute filesystem path
    - ``FILE`` — filename only, no directory component

    When ``link_path=True`` and the resolved path is absolute, a ``file://``
    URI is generated for terminal hyperlink support.

    When ``inject_base_record=True``, ``record.pathname`` is also updated so
    stdlib formatters see the normalised path.
    """

    resolution_mode: PathResolutionSetting = PathResolutionSetting.RELATIVE
    _project_root: Path | None = None
    link_path: bool = True
    inject_base_record: bool = False

    def __init__(self, name: str = "",
                 resolution_mode: PathResolutionSetting = PathResolutionSetting.RELATIVE,
                 link_path: bool = True,
                 inject_base_record: bool = False):
        """Initialize with resolution mode, link path generation flag, and optional base-record injection."""
        super().__init__(name)
        self.resolution_mode = resolution_mode
        self.link_path = link_path
        self.inject_base_record = inject_base_record

    @property
    def project_root(self):
        if self._project_root is None and not self.resolution_mode == PathResolutionSetting.FILE:
            self._project_root = resolve_project_root()
            if not self._project_root:
                self.resolution_mode = PathResolutionSetting.FILE
        return self._project_root

    @project_root.setter
    def project_root(self, value: Path | None):
        """Override the project root used for RELATIVE resolution; ``None`` re-enables auto-detection."""
        self._project_root = value

    def filter(self, record: LogRecord) -> bool:
        """Resolve and write normalised path attributes onto ``record.spark``; always returns True."""
        if not has_spark_extra_attributes(record):
            record.spark = SparkRecordAttrs.from_record(record)

        display_path = self._handle_path_resolution(record)
        link_path = self._handle_link_uri(record)

        spark = cast(HasSparkAttributes, record).spark
        spark.filename = display_path.name
        spark.filepath = display_path
        spark.uri = link_path
        spark.lineno = record.lineno
        spark.function = record.funcName

        if self.inject_base_record:
            record.pathname = str(display_path)
            record.uri = link_path

        return True

    def _handle_path_resolution(self, record: LogRecord) -> Path:
        """Apply the configured resolution mode to produce the display path."""
        if has_spark_extra_attributes(record):
            path = record.spark.filepath
        else:
            path = Path(record.pathname)

        try:
            if self.resolution_mode == PathResolutionSetting.RELATIVE and self.project_root:
                display_path = Path(path.relative_to(self.project_root).as_posix())
            elif self.resolution_mode == PathResolutionSetting.ABSOLUTE:
                display_path = Path(path.absolute().as_posix())
            else:
                display_path = Path(path.name)
        except ValueError:
            display_path = Path(path.name)
        return display_path

    def _handle_link_uri(self, record: LogRecord) -> str | None:
        """Return a ``file://`` URI for terminal hyperlinks when link_path is enabled and the path is absolute."""
        if has_spark_extra_attributes(record):
            path = record.spark.filepath
        else:
            path = Path(record.pathname)

        if self.link_path and path.is_absolute():
            link_path = path.as_uri()
        else:
            link_path = None

        return link_path
