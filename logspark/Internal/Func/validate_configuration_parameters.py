import logging
from typing import Optional, Union

from ...Types import InvalidConfigurationError
from ...Types import PresetOptions, TracebackOptions


def validate_configuration_parameters(
    level: int,
    traceback: Union[TracebackOptions, str, None],
    handler: Optional[logging.Handler],
    preset: Optional[Union[PresetOptions, str]]  ,
    no_freeze: bool
) -> tuple[TracebackOptions, Optional[PresetOptions]]:
    """
    Validate configuration parameters

    Raises:
        InvalidConfigurationError: If any parameter is invalid
    """
    # Validate level is a valid integer (stdlib logging accepts any integer)
    if not isinstance(level, int):
        raise InvalidConfigurationError(f"level must be an integer, got {type(level)}")

    # Validate traceback
    traceback = _resolve_traceback_options(traceback)

    # validate preset
    preset = _resolve_preset_options(preset)

    # Validate format is a Handlers instance (can be None for default)
    if handler is not None and not isinstance(handler, logging.Handler):
        raise InvalidConfigurationError(
            f"handler must be a logging.Handlers instance, got {type(handler)}"
        )

    if not isinstance(no_freeze, bool):
        raise InvalidConfigurationError(
                f"no_freeze must be a bool, got {type(no_freeze)}"
                )

    return traceback, preset

def _resolve_traceback_options(traceback: Union[TracebackOptions, str, None]) -> TracebackOptions:
    traceback_map = {
        "none": TracebackOptions.NONE,
        "compact": TracebackOptions.COMPACT,
        "full": TracebackOptions.FULL,
    }

    # Convert string traceback to enum if needed
    if traceback is None:
        traceback = TracebackOptions.NONE
    if isinstance(traceback, str):
        traceback_map = {
            "none": TracebackOptions.NONE,
            "compact": TracebackOptions.COMPACT,
            "full": TracebackOptions.FULL,
        }
        traceback_lower = traceback.lower()
        if traceback_lower not in traceback_map:
            raise InvalidConfigurationError(
                f"Invalid traceback option '{traceback}'. "
                f"Valid options: {list(traceback_map.keys())}"
            )
        traceback = traceback_map[traceback_lower]

    if not isinstance(traceback, TracebackOptions):
        raise InvalidConfigurationError(
            f"Invalid traceback traceback option '{traceback}'. "
            f"Valid options: {list(traceback_map.keys())}"
        )
    return traceback

def _resolve_preset_options(preset: Optional[Union[PresetOptions, str]]) -> Optional[PresetOptions]:
    preset_map = {
                "terminal": PresetOptions.TERMINAL,
                "json": PresetOptions.JSON,
            }

    if isinstance(preset, str):
        preset_map = {
            "terminal": PresetOptions.TERMINAL,
            "json": PresetOptions.JSON,
        }
        preset = preset.lower()
        if preset not in preset_map:
            raise InvalidConfigurationError(
                f"Invalid preset option '{preset}'. "
                f"Valid options: {list(preset_map.keys())}"
            )
        preset = preset_map[preset]

    if preset is not None and not isinstance(preset, PresetOptions):
        raise InvalidConfigurationError(
            f"Invalid preset option '{preset}'. Valid options: {list(preset_map.keys())}"
        )
    return preset