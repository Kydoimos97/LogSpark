def validate_level(level: str | int) -> int:
    """
    Validate and normalize a logging level using stdlib registration.

    Accepts either a numeric level or a level name. Only levels that are
    registered with the standard logging module are considered valid.

    This mirrors stdlib behavior while providing stricter validation:
    - Numeric levels must have a registered name
    - Named levels must resolve to a numeric value
    - User-registered custom levels are fully supported

    Args:
        level: Logging level as int or registered level name.
               Strings are case-sensitive.

    Returns:
        The corresponding numeric logging level.

    Raises:
        KeyError: If the level is not registered with logging.
        TypeError: If the level type is unsupported.
    """
    from logging import _levelToName, _nameToLevel

    if isinstance(level, int):
        # Ensure the numeric level is registered
        if level not in _levelToName:
            raise KeyError(f"Invalid level: {level}")
        return level

    if isinstance(level, str):
        # Resolve name to numeric level
        result = _nameToLevel.get(level)
        if result is None:
            raise KeyError(f"Invalid level: {level}")
        return result

    raise TypeError(f"Invalid level type: {type(level)}")
