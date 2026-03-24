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
    resolution_mode: PathResolutionSetting = PathResolutionSetting.RELATIVE
    _project_root: Path | None = None
    link_path: bool = True
    inject_base_record: bool = False

    def __init__(self, name: str = "",
                 resolution_mode: PathResolutionSetting = PathResolutionSetting.RELATIVE,
                 link_path: bool = True,
                 inject_base_record: bool = False):
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
        "can override but wouldn't do so. also can use a ENV var."
        self._project_root = value

    def filter(self, record: LogRecord) -> bool:
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
        if has_spark_extra_attributes(record):
            path = record.spark.filepath
        else:
            path = Path(record.pathname)

        if self.link_path and path.is_absolute():
            link_path = path.as_uri()
        else:
            link_path = None

        return link_path
