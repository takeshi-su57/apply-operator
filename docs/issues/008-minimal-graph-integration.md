# [Feature]: Wire minimal graph and run end-to-end (first milestone)

**Labels:** `enhancement`, `priority:high`
**Depends on:** [004](004-resume-structured-extraction.md), [006](006-search-jobs-node.md), [007](007-analyze-fit-node.md)

## Description

Wire up parse_resume, search_jobs, analyze_fit, and report_results into a working LangGraph and run the pipeline end-to-end. `fill_application` is a stub (marks job as applied, advances index) — the real browser form filling comes in [009](009-fill-application-node.md).

## Motivation

- Validates the graph structure, state flow, and conditional routing before tackling the hardest node
- First time you see the full LangGraph lifecycle: compile, invoke, stream, observe results
- **This is the first milestone** — after this, you have a working (if incomplete) agent

## Implementation

### 1. `fill_application` stub (`nodes/fill_application.py`)

The stub marks the current job as applied and advances the pipeline — no real form filling yet (deferred to issue 009). Uses `model_copy()` to immutably update the job:

```python
jobs[idx] = jobs[idx].model_copy(update={"applied": True})
return {
    "jobs": jobs,
    "current_job_index": idx + 1,
    "total_applied": state.total_applied + 1,
}
```

### 2. Rich progress display via streaming (`main.py`)

Replaced `graph.ainvoke()` with `graph.astream(state, stream_mode="updates")` to display real-time progress. Each node completion prints a green checkmark:

```
  ✓ parse_resume
  ✓ search_jobs
  ✓ analyze_fit
  ✓ fill_application
  ✓ report_results
```

Node outputs are accumulated into a flat dict via `.update()`. A `None` guard handles nodes that return empty results (e.g., `report_results` returns `{}`).

### 3. Integration tests (`tests/test_graph.py`)

12 tests covering compilation, pipeline routing, streaming, and CLI output:

| Test | What it verifies |
|------|-----------------|
| `test_graph_compiles` | `build_graph()` returns without error |
| `test_graph_has_expected_nodes` | All 6 nodes + `__start__`/`__end__` present |
| `test_mixed_fit_scores` | 2 applied (>=0.6), 1 skipped (<0.6) |
| `test_no_jobs_found` | Empty jobs list terminates without calling analyze_fit |
| `test_all_low_fit` | All 3 jobs skipped, none applied |
| `test_all_high_fit` | All 2 jobs applied |
| `test_single_job_applied` | Single high-fit job marked applied |
| `test_single_job_skipped` | Single low-fit job marked skipped |
| `test_report_results_writes_json` | JSON output written to disk |
| `test_streaming_yields_all_node_names` | `astream` yields events for every node |
| `test_streaming_state_matches_ainvoke` | Accumulated stream state matches `ainvoke` result |
| `test_prints_results_from_streamed_state` | `_print_results` renders Rich table correctly |

Mocking strategy: patch node functions at the `apply_operator.graph` module level before `build_graph()` so the compiled graph uses mock functions. External I/O (LLM, browser, PDF) is never called.

### Key decisions

- **`stream_mode="updates"` over `"values"`**: updates mode yields `{node_name: output_dict}` which lets us both display progress and accumulate state. The `"values"` mode yields the full state but doesn't expose node names.
- **`model_copy()` over mutation**: Pydantic objects in the jobs list are immutable by convention. The stub creates a copy with `applied=True` rather than mutating in place.
- **`None` guard on stream accumulation**: `report_results` returns `{}` which LangGraph can serialize as `None` in stream events. Both `main.py` and tests guard against this.

### What `graph.py` and `report_results.py` already had

Both were already fully implemented before this issue:
- `graph.py` — all nodes, edges, conditional routing (`should_apply`, `has_more_jobs`, `skip_job`)
- `report_results.py` — writes `data/results.json`, logs summary counts

No changes were needed in either file.

## Acceptance Criteria

- [x] `build_graph()` compiles without errors
- [x] `python -m apply_operator run --resume resume.pdf --urls urls.txt` executes the full pipeline
- [x] All jobs are analyzed and scored
- [x] High-fit jobs marked as "applied" (stub), low-fit jobs "skipped"
- [x] Results saved to `data/results.json`
- [x] Results table printed to console with Rich formatting
- [x] No infinite loops — pipeline terminates for any input
- [x] Integration test passes with mocked dependencies (12 tests)
- [x] `ruff check` and `mypy` pass (93/93 tests, 0 errors)

## Files Changed

| File | Change |
|------|--------|
| `src/apply_operator/nodes/fill_application.py` | Stub: mark job applied, increment counter, log |
| `src/apply_operator/main.py` | Replace `ainvoke` with `astream` + Rich progress display |
| `tests/test_graph.py` | New: 12 integration tests |
| `docs/issues/008-minimal-graph-integration.md` | Updated with implementation details |

## Related Issues

- Blocked by [004](004-resume-structured-extraction.md), [006](006-search-jobs-node.md), [007](007-analyze-fit-node.md)
- Blocks [009](009-fill-application-node.md), [010](010-cli-progress-and-reporting.md), [011](011-error-handling-and-retry.md), [012](012-langgraph-checkpointing.md)
