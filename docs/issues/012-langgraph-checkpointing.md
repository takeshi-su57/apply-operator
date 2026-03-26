# [Feature]: Add LangGraph checkpointing for resume-on-crash

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

Add LangGraph's built-in checkpointing so the agent saves state after each node. If the process crashes or is interrupted at job 8/10, it can resume from where it left off without redoing jobs 1-7.

## Motivation

- A full run can take 10-30+ minutes — losing progress on crash is unacceptable
- LangGraph has built-in SQLite checkpointing — minimal implementation effort
- Adds a `resume` CLI command for interrupted runs

## Proposed Solution

### SQLite checkpointer

```python
from langgraph.checkpoint.sqlite import SqliteSaver

def build_graph(checkpoint_path="data/checkpoints.db"):
    checkpointer = SqliteSaver(db_path=checkpoint_path)
    return graph.compile(checkpointer=checkpointer)
```

### Thread ID management

Each run gets a unique thread ID. Pass via config:
```python
config = {"configurable": {"thread_id": "run-2026-03-25-001"}}
result = graph.invoke(initial_state, config=config)
```

### Resume from checkpoint

```python
# Pass None as state → LangGraph loads from checkpoint
result = graph.invoke(None, config={"configurable": {"thread_id": thread_id}})
```

### New CLI commands

- `apply-operator resume` — resume last interrupted run
- `apply-operator list-runs` — show past runs with status

## Alternatives Considered

- **Manual state serialization to JSON** — more work, doesn't integrate with LangGraph's graph execution
- **PostgreSQL checkpointer** — overkill for single-user; SQLite is sufficient

## Acceptance Criteria

- [ ] State saved to SQLite after each node
- [ ] `resume` command continues from last checkpoint
- [ ] Completed runs are not re-run
- [ ] Corrupted checkpoint doesn't crash (graceful error)
- [ ] `list-runs` shows past runs with status
- [ ] Tests cover save, resume, and corruption
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/graph.py` — add checkpointer
- `src/apply_operator/main.py` — add `resume` and `list-runs` commands
- `src/apply_operator/config.py` — add checkpoint path
- `tests/test_checkpointing.py` — create

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
