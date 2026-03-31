# [Refactor]: Refine state model based on implementation learnings

**Labels:** `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

Migrate `ApplicationState` from Pydantic `BaseModel` to `TypedDict` with LangGraph reducers. The `errors` field now uses `Annotated[list[str], operator.add]` so each node returns only its new errors and the framework handles accumulation.

`ResumeData` and `JobListing` remain Pydantic `BaseModel` for validation.

## Motivation

- LangGraph natively uses `TypedDict` with `Annotated` reducers
- The `errors` field was fragile: nodes had to manually copy and re-include all prior errors (`[*state.errors, "new"]`), and a node returning `{"errors": ["new"]}` would silently overwrite all prior errors
- With `operator.add` reducer, nodes return only new errors and the framework concatenates automatically

## Implementation

### TypedDict with reducer

```python
import operator
from typing import Annotated, TypedDict

class ApplicationState(TypedDict, total=False):
    resume_path: str
    job_urls: list[str]
    resume: ResumeData
    jobs: list[JobListing]
    current_job_index: int
    total_applied: int
    total_skipped: int
    errors: Annotated[list[str], operator.add]
```

### Key behavioral change

**Before:** Nodes had to manually preserve prior errors:
```python
errors = list(state.errors)
errors.append("new error")
return {"errors": errors}
```

**After:** Nodes return only new errors:
```python
return {"errors": ["new error"]}
```

### State access pattern change

All node and routing functions changed from attribute access to dict access:
- `state.resume_path` -> `state["resume_path"]`
- `state.jobs[idx]` -> `state["jobs"][idx]`
- `state.resume.name` -> `state["resume"].name` (ResumeData is still Pydantic)

### Streaming error accumulation

In `main.py`, streaming events now contain only per-node errors. The `_run_graph` function accumulates errors with `extend()` instead of `update()`.

## Alternatives Considered

- **Keep Pydantic** -- would avoid the migration effort, but the error overwrite bug was a real risk and LangGraph works better with TypedDict

## Acceptance Criteria

- [x] State model is clean, well-documented, with no unused fields
- [x] Reducers work correctly (errors append, not replace)
- [x] All nodes and tests updated for new state shape
- [x] All tests pass (193 tests)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/state.py` -- `ApplicationState` migrated to TypedDict
- `src/apply_operator/graph.py` -- dict access in routing functions
- `src/apply_operator/nodes/parse_resume.py` -- dict access + reducer errors
- `src/apply_operator/nodes/search_jobs.py` -- dict access + reducer errors
- `src/apply_operator/nodes/analyze_fit.py` -- dict access + reducer errors
- `src/apply_operator/nodes/fill_application.py` -- dict access + reducer errors
- `src/apply_operator/nodes/report_results.py` -- dict access
- `src/apply_operator/main.py` -- dict initial state, streaming error accumulation, simplified `_print_results`
- `tests/conftest.py` -- `sample_state` fixture as dict
- `tests/test_graph.py` -- dict state, dict access in fakes
- `tests/test_checkpoint.py` -- dict state, dict access in fakes
- `tests/test_parse_resume.py` -- dict state, updated error test
- `tests/test_analyze_fit.py` -- dict state, updated error test
- `tests/test_fill_application.py` -- dict state
- `tests/test_search_jobs.py` -- dict state

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
