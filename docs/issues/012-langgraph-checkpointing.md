# [Feature]: Add LangGraph checkpointing for resume-on-crash

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

Add LangGraph's built-in checkpointing so the agent saves state after each node. If the process crashes or is interrupted at job 8/10, it can resume from where it left off without redoing jobs 1-7.

## Motivation

- A full run can take 10-30+ minutes — losing progress on crash is unacceptable
- LangGraph has built-in SQLite checkpointing — minimal implementation effort
- Adds `resume` and `list-runs` CLI commands for interrupted runs

## Implementation

### AsyncSqliteSaver for graph execution

LangGraph's sync `SqliteSaver` does not support async methods (`astream`, `ainvoke`). The implementation uses `AsyncSqliteSaver` (from `langgraph-checkpoint-sqlite` + `aiosqlite`) for graph streaming, and sync `SqliteSaver` for read-only operations (`list-runs`, pre-flight checks in `resume`).

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string("data/checkpoints.sqlite") as saver:
    graph = build_graph(checkpointer=saver)
    await graph.astream(initial, config=config, stream_mode="updates")
```

### Thread ID management

Each run gets a unique thread ID (`run-{unix_timestamp}`). Passed via config:
```python
config = {"configurable": {"thread_id": "run-1711234567"}}
```

### Resume from checkpoint

```python
# Pass None as state → LangGraph loads from checkpoint
result = await graph.ainvoke(None, config={"configurable": {"thread_id": thread_id}})
```

Pre-flight checks use sync `SqliteSaver` + `graph.get_state(config)` to verify the run exists and is not already completed before streaming.

### Corruption handling

`create_checkpointer()` and `create_async_checkpointer()` catch `sqlite3.DatabaseError` and fall back to an in-memory SQLite saver with a warning log.

### New CLI commands

- `apply-operator resume <run-id>` — resume an interrupted run from its last checkpoint
- `apply-operator list-runs` — show past runs with status (Completed/Interrupted)

### Configuration

- `CHECKPOINT_DB` env var (default: `data/checkpoints.sqlite`) controls the SQLite path
- Added to `config.py` as `checkpoint_db` setting

## Alternatives Considered

- **Manual state serialization to JSON** — more work, doesn't integrate with LangGraph's graph execution
- **PostgreSQL checkpointer** — overkill for single-user; SQLite is sufficient
- **Sync SqliteSaver** — does not support `astream()`/`ainvoke()`, raises `NotImplementedError`

## Acceptance Criteria

- [x] State saved to SQLite after each node
- [x] `resume` command continues from last checkpoint
- [x] Completed runs are not re-run
- [x] Corrupted checkpoint doesn't crash (graceful error)
- [x] `list-runs` shows past runs with status
- [x] Tests cover save, resume, and corruption (11 tests)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `pyproject.toml` — added `langgraph-checkpoint-sqlite` and `aiosqlite` dependencies
- `src/apply_operator/checkpoint.py` — **new**: checkpointer factories, thread ID generation, run summaries
- `src/apply_operator/graph.py` — `build_graph()` accepts optional `checkpointer` param
- `src/apply_operator/main.py` — updated `run` command, added `resume` and `list-runs` commands
- `src/apply_operator/config.py` — added `checkpoint_db` setting
- `.env.example` — added `CHECKPOINT_DB`
- `tests/test_checkpoint.py` — **new**: 11 tests for checkpointing
- `tests/conftest.py` — added `checkpoint_saver` and `async_checkpoint_saver` fixtures

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
