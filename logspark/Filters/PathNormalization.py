import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .._Internal import SparkFilterModule
from .._Internal.State import resolve_project_root
from ..Types.Options import PathResolutionSetting
from .TracebackPolicy import SupportsExceptionOrigin


@dataclass(slots=True, frozen=True)
class ResolvedPath:
    path: Path
    uri: str | None
    lineno: int | None
    function: str | None


@runtime_checkable
class SupportsResolvedPath(Protocol):
    resolved_path: ResolvedPath


class PathNormalization(SparkFilterModule):
    _path_mode: PathResolutionSetting = PathResolutionSetting.RELATIVE
    _project_root: Path | None = None
    _enable_link_path: bool = True

    def _ext_init(self) -> None:
        project_root = resolve_project_root()
        if project_root is None:
            self._path_mode = PathResolutionSetting.FILE
        else:
            self._project_root = project_root

    def configure(
        self,
        *,
        path_resolution_mode: PathResolutionSetting | None = None,
        project_root: Path | None = None,
        path_link_enabled: bool | None = None,
            **kwargs: Any,
    ) -> None:
        if path_resolution_mode:
            self._path_mode = path_resolution_mode
        if project_root:
            self._project_root = project_root
        if path_link_enabled is not None:
            self._enable_link_path = path_link_enabled

    def filter(self, record: logging.LogRecord) -> bool:
        display_path = self._handle_path_resolution(record)
        link_path = self._handle_link_uri(record)

        record.resolved_path = ResolvedPath(display_path, link_path, record.lineno, record.funcName)

        if self._inject:
            record.pathname = str(display_path)
            record.uri = link_path

        return True

    def _handle_path_resolution(self, record: logging.LogRecord) -> Path:
        if isinstance(record, SupportsExceptionOrigin):
            path = record.exc_origin.filepath
        else:
            path = Path(record.pathname)

        try:
            if self._path_mode == PathResolutionSetting.RELATIVE and self._project_root:
                display_path = Path(path.relative_to(self._project_root).as_posix())
            elif self._path_mode == PathResolutionSetting.ABSOLUTE:
                display_path = Path(path.absolute().as_posix())
            else:
                display_path = Path(path.name)
        except ValueError:
            display_path = Path(path.name)

        return display_path

    def _handle_link_uri(self, record: logging.LogRecord) -> str | None:
        if isinstance(record, SupportsExceptionOrigin):
            path = record.exc_origin.filepath
        else:
            path = Path(record.pathname)

        if self._enable_link_path and path.is_absolute():
            link_path = path.as_uri()
        else:
            link_path = None

        return link_path
