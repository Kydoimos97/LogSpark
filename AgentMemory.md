## Todo
- [x] Fix pyproject.toml: wrong PyPI URL, missing [project.optional-dependencies], versioning
- [x] Address v1 readiness gaps

---

## Global Notes
[2026-04-01 00:00] LogSpark is a singleton logger library. Tests: 392 passing. Branch: feature/v1. VCS versioning via hatch-vcs, no git tags exist yet.

---

## Additional Guidance

---

## Memories
[2026-04-01 00:00] V1 readiness review: two hard blockers — (1) pyproject.toml PyPI URL points to "xpytools" project, (2) optional extras (color/json/trace) declared as [dependency-groups] not [project.optional-dependencies], so pip install logspark[color] will fail at PyPI. README links to xpytools.readthedocs.io. Docs exist at docs/ (1099 lines across 9 files) but README.md itself is a stub. todo.md has a responsibility-split refactor planned for post-v1.
[2026-04-01 00:00] All v1 blockers fixed: static version 1.0.0 (dropped hatch-vcs), [project.optional-dependencies] added with color/json/trace/all extras, PyPI URL corrected, README docs URL fixed, adopt_all list mutation fixed, addHandler lock gap fixed, Taskfile run-demo path fixed, todo.md cleared. 392 tests pass.
