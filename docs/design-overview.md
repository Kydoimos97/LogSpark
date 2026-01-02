# LogSpark Overview

LogSpark is a **thin integration and policy layer** over Python's standard logging ecosystem. It extends stdlib logging without replacing it.

## What LogSpark Deliberately Avoids

LogSpark is designed so you can use **parts** of it without committing to the whole system.

**No custom logging APIs.** All logging methods are standard: `debug()`, `info()`, `warning()`, `error()`, `critical()`. No new concepts to learn.

**No framework logger lock-in.** Handlers work with any stdlib logger. Filters integrate with existing infrastructure. Rich integrations obey Liskov substitution.

**No reimplementation of proven components.** Stdlib logging and Rich are heavily tested by large user bases. Reimplementing their logic would reduce predictability and increase maintenance risk. LogSpark composes proven components instead of rewriting them.

**No monolithic adoption requirement.** Use handlers independently. Add filters to existing loggers. Introduce the singleton gradually. Each component provides value without forcing migration.

## Why the Singleton Exists: Ambiguity is Dangerous

In stdlib logging, logger identity and behavior are often unclear in deep stacks:

```python
# Which logger am I actually using?
logger = logging.getLogger(__name__)

# Who configured it? What handlers apply?
# Did pytest alter capture behavior?
# Did a dependency mutate root logger state?
# Is configuration order-dependent?
```

Consider this common scenario:
```python
# myapp/service.py
import logging
logger = logging.getLogger(__name__)  # "myapp.service"

def process_data():
    logger.info("Processing started")  # Which handlers? What format?

# tests/test_service.py  
def test_process_data():
    # pytest may have altered logging capture
    # third-party fixtures may have added handlers
    # root logger state may have propagated
    process_data()  # Unpredictable logging behavior
```

You cannot reliably answer:

- Which logger you are actually using
- Who configured it
- What handlers, filters, and guarantees apply

LogSpark uses a singleton as a **guardrail** against this ambiguity:

- Stable identity across all contexts
- Explicit, centralized configuration  
- Predictable lifecycle and behavior

The singleton stabilizes identity, not ownership of logging.

## Non-Goals

LogSpark explicitly does not provide:

- **Async logging** - Uses stdlib synchronous logging only
- **Runtime reconfiguration** - Configuration is immutable after freeze
- **Ownership of stdlib logging registry** - Operates via snapshot and mutation
- **Logger proxying/interception** - Direct delegation to stdlib loggers

## Explicit Configuration Prevents Drift

Configuration drift is an operational failure mode. Runtime flexibility in logging setup is not a virtue.

Implicit logging configuration leads to:

- Hidden dependencies between modules
- Environment-specific behavior that breaks in production
- Formatting and handler drift that breaks observability pipelines  
- Alert noise and pager fatigue from inconsistent output

LogSpark enforces operational discipline:

- Explicit `configure()` call at startup
- Warning when logging is used unconfigured
- Immutable behavior after freeze
- `kill()` strictly for testing scenarios

## Composition Over Reimplementation

LogSpark provides **minimal configuration surface** - typically 3 lines at the top of your application:

```python
from logspark import spark_logger
spark_logger.configure(level=logging.INFO, preset="json")
# Done. Full compatibility with existing logging code.
```

This approach prioritizes:

- **Predictability**: Behavior is determined by well-tested stdlib and Rich components
- **Trust**: No custom logging logic to debug or maintain
- **Reliability**: Composition of proven components reduces maintenance risk