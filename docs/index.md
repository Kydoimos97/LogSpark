<div align="center">
<img alt="Logo.png" src="assets/Logo.png" width="250" height="250"/>
</div>

LogSpark is a configuration and integration layer over Python's standard `logging` module.

It does not replace stdlib logging. It does not introduce a new logging API. If you know stdlib, you already know how to use LogSpark's components. What LogSpark adds is lifecycle enforcement, environment-aware policy, and a corrected set of defaults that stdlib leaves to the user.

---

## What problem does it solve?

Python's `logging` module is reliable and well-designed, but it leaves too many operational decisions implicit:

- Logging works before anyone has configured it, silently
- Any module anywhere can mutate the root logger
- Configuration order matters and is never enforced
- Traceback verbosity, output format, and stream selection are all left to you

The result is logging that works fine in development and breaks or disappears in production.

LogSpark fixes the operational layer, not the logging layer. The stdlib dispatch, record semantics, and handler mechanics are untouched.

---

## What it is not

- Not a structured logging framework (though it supports JSON output)
- Not a drop-in replacement for `loguru`, `structlog`, or similar
- Not a wrapper that intercepts or proxies log calls
- Not a new API: handlers, filters, and formatters are plain stdlib objects

---

## Core features

| Feature | What it gives you |
|---|---|
| Lifecycle enforcement | `configure -> freeze -> use`: configuration happens once, explicitly |
| Output modes | Terminal (color, Rich layout) or JSON, switchable via environment variable |
| Traceback control | Hide, compact, or full tracebacks per-logger |
| Scoped debugging | Temporarily lower the log level for a function or block without changing config |
| Dependency management | Suppress or unify noisy third-party loggers without touching their code |
| stdlib compatibility | Every component works standalone with any `logging.Logger` |

---

## Navigation

- [Concepts](concepts.md): How to think about the pipeline and where LogSpark fits.
- [Glossary](glossary.md): Definitions for every component and term. Use as reference.
- [Quickstart](quickstart.md): Working logger in five lines.
- [Lifecycle](lifecycle.md): The configure -> freeze -> use model in depth.
- [Output Modes](output-modes.md): Terminal vs JSON, traceback policy, path resolution.
- [Environment Variables](environment.md): Operational control without code changes.
- [Advanced Usage](advanced.md): Scoped log levels, managing third-party loggers.
- [Component Reference](reference.md): Full API for all handlers, filters, and formatters.
