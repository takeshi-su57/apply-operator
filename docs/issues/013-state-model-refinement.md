# [Refactor]: Refine state model based on implementation learnings

**Labels:** `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

After the first working pipeline, refine `ApplicationState` based on what worked and what didn't. Evaluate migrating from Pydantic `BaseModel` to `TypedDict` with LangGraph reducers, and add/remove fields discovered during implementation.

## Motivation

- The initial state model was designed before implementation — real usage reveals gaps
- LangGraph natively uses `TypedDict` with `Annotated` reducers; Pydantic may cause friction
- Reducers prevent common bugs (e.g., `errors` being overwritten instead of appended)

## Proposed Solution

### Evaluate TypedDict migration

```python
from typing import TypedDict, Annotated
import operator

class ApplicationState(TypedDict):
    resume_path: str
    job_urls: list[str]
    resume: ResumeData
    jobs: list[JobListing]
    current_job_index: int
    total_applied: int
    total_skipped: int
    errors: Annotated[list[str], operator.add]  # append, don't replace
```

### Reducer concept

Without reducer: `errors` is replaced by the return value.
With `operator.add` reducer: `errors` is **appended** to. Multiple nodes can add errors without overwriting each other.

### Potential new fields

- `cover_letter: str` — if cover letter generation is added (issue 014)
- `screenshots: list[str]` — debug screenshot paths
- `start_time: float` — for duration tracking

## Alternatives Considered

- **Keep Pydantic** — if it works well in practice, no reason to migrate. Only migrate if you hit friction.

## Acceptance Criteria

- [ ] State model is clean, well-documented, with no unused fields
- [ ] Reducers work correctly (errors append, not replace)
- [ ] All nodes and tests updated for new state shape
- [ ] All tests pass
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/state.py` — refine or migrate
- `src/apply_operator/nodes/*.py` — update for new state shape
- `src/apply_operator/graph.py` — update if TypedDict changes needed
- `tests/conftest.py` — update fixtures
- `tests/*.py` — update for new state shape

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
