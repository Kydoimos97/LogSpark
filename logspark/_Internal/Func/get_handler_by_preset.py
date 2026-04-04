import logging

from ...Types.Options import PathResolutionSetting, PresetOptions, TracebackOptions


def get_handler_by_preset(
        preset: PresetOptions, traceback: TracebackOptions | None, path_resolution: PathResolutionSetting | None, ) -> logging.Handler:
    # if handler is none but handler_preset isn't we apply the handler_preset
    _handler: logging.Handler | None = None
    if preset == PresetOptions.TERMINAL or preset is None:
        from ..State import is_rich_available

        if is_rich_available():
            from ...Handlers.Rich.SparkRichHandler import SparkRichHandler

            _handler = SparkRichHandler()
        else:
            from ...Handlers import SparkTerminalHandler

            _handler = SparkTerminalHandler()

    elif preset == PresetOptions.JSON:
        from ...Handlers import SparkJsonHandler

        _handler = SparkJsonHandler()
    else:
        # invalid handler_preset
        raise ValueError(f"Invalid handler_preset '{preset}'")
    assert _handler is not None
    # if traceback is not None:
    #     _t_filter: TracebackPolicyFilter = TracebackPolicyFilter()
    #     _t_filter.configure(traceback_policy=traceback)
    #     # If we use our own handler we know we own the downstream so injection is safe
    #     _t_filter.set_injection(True)
    #     _handler.addFilter(_t_filter)
    # if path_resolution is not None:
    #     _p_filter: PathNormalizationFilter = PathNormalizationFilter()
    #     _p_filter.configure(path_resolution_mode=path_resolution)
    #     _p_filter.set_injection(True)
    #     _handler.addFilter(_p_filter)
    return _handler
