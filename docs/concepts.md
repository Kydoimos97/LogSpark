# Concepts

LogSpark is built on top of stdlib logging, so the same four components exist: loggers, handlers, filters, and formatters. The names carry over, but in LogSpark each one has a more specific role than stdlib leaves implied.

This page covers how to think about them in the context of LogSpark. For precise definitions of each component, see the [Glossary](glossary.md).

---

## The pipeline

Every log call travels through a fixed pipeline:

```
your code
    |
Logger      -- is this record worth creating?
    |
Filter(s)   -- enrich the record with additional context
    |
Handler(s)  -- where does this record go?
    |
Formatter   -- what does it look like when it gets there?
```

The most important thing to carry from this: filters in LogSpark are primarily enrichment, not exclusion. They attach structured data to the record (file paths, trace IDs, exception metadata) so handlers and formatters have more to work with. The "filter" name implies gating, but that is the secondary use case.

---

## Where LogSpark sits

LogSpark does not replace any of these stages. Stdlib is still the execution engine. What LogSpark adds is:

- A lifecycle around the logger: configuration happens once, explicitly, and is locked after that
- Defaults that production use requires but stdlib leaves unspecified: JSON output, traceback control, path normalization
- Coordination utilities for managing loggers you do not own: third-party libraries, the root logger

---

## Where to go next

- First time here: [Quickstart](quickstart.md)
- Component definitions: [Glossary](glossary.md)
- Something behaving unexpectedly: [Lifecycle](lifecycle.md)
