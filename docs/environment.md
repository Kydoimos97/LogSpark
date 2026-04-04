# Environment Variables

LogSpark uses environment variables for operational control: behaviors that should differ between environments (local, CI, production) without requiring code changes.

---

## LOGSPARK_MODE

Controls the performance and output profile of the logger.

```bash
export LOGSPARK_MODE=fast
```

| Value | Behavior |
|---|---|
| *(unset)* | Default mode. Full call-site resolution, standard output behavior. |
| `fast` | Constant-time stacklevel resolution. Skips per-call frame walking. File and line numbers in log output may be less precise. Use in CI or high-throughput environments where call-site accuracy is secondary to performance. |
| `silenced` | Full logging pipeline remains active (records are created, filters run, handlers execute) but output is discarded. Use for testing logging correctness without producing output. |

`fast` and `silenced` solve different problems. `fast` is a performance optimization. `silenced` is a testing tool. Do not conflate them.

---

## PROJECT_ROOT

Overrides LogSpark's automatic project root detection. Used by [`PathNormalizationFilter`](reference.md#pathnormalizationfilter) to compute relative file paths in log lines.

```bash
export PROJECT_ROOT=/home/app
```

When unset, LogSpark resolves the project root in this order:

1. `VIRTUAL_ENV` parent directory (if set)
2. Upward search from `cwd` for `pyproject.toml`, `.git`, or `requirements.txt`
3. Falls back to filename-only display if nothing is found

Set this explicitly in containerized environments where the working directory may not match the project root.

See [Output Modes: Path resolution](output-modes.md#path-resolution).

---

## FORCE_COLOR / NO_COLOR

Standard environment variables for controlling ANSI color output. LogSpark respects both.

```bash
export FORCE_COLOR=1   # Force color output even in non-TTY environments
export NO_COLOR=1      # Disable color output unconditionally
```

These follow the [no-color.org](https://no-color.org) convention. `FORCE_COLOR` takes priority if both are set.

---

## TTY_COMPATIBLE

LogSpark-specific override for color capability detection, for cases where automatic detection gives the wrong result.

```bash
export TTY_COMPATIBLE=1   # Force color-compatible mode
export TTY_COMPATIBLE=0   # Force non-color mode
```

Use this when your terminal supports ANSI colors but LogSpark's detection heuristics disagree, for example in some SSH configurations or custom terminal emulators.

---

## VIRTUAL_ENV

Not set by LogSpark, but read during project root resolution. If present, LogSpark uses the virtual environment's parent directory as the project root fallback. Set automatically by most virtual environment tools (`venv`, `poetry`, `pyenv`).

See [PROJECT_ROOT](#project_root) above.
