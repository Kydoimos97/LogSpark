def generate_stdlib_format(
    show_time: bool, show_level: bool, level_width: int, show_path: bool, show_function: bool
) -> str:
    # "%(asctime)-10s - %(levelname)-8s - %(filename)s:%(lineno)d -> %(message)s",
    format_parts = []
    if show_time:
        format_parts.append("%(asctime)s")
    if show_level:
        format_parts.append(f"%(levelname)-{level_width}s")
    if show_path:
        format_parts.append("%(filename)s:%(lineno)d")
    if show_function:
        format_parts.append("%(funcName)s")
    format_str = " - ".join(format_parts)
    format_str += " -> %(message)s"
    return format_str
