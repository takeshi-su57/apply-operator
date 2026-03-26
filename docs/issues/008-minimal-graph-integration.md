# [Feature]: Wire minimal graph and run end-to-end (first milestone)

**Labels:** `enhancement`, `priority:high`
**Depends on:** [004](004-resume-structured-extraction.md), [006](006-search-jobs-node.md), [007](007-analyze-fit-node.md)

## Description

Wire up parse_resume, search_jobs, analyze_fit, and report_results into a working LangGraph and run the pipeline end-to-end. `fill_application` is a stub (marks job as applied, advances index) — the real browser form filling comes in [009](009-fill-application-node.md).

## Motivation

- Validates the graph structure, state flow, and conditional routing before tackling the hardest node
- First time you see the full LangGraph lifecycle: compile, invoke, stream, observe results
- **This is the first milestone** — after this, you have a working (if incomplete) agent

## Proposed Solution

1. Implement stub `fill_application` (advance index + mark applied)
2. Implement `report_results` (save JSON to `data/results.json`)
3. Verify `graph.py` compiles: `build_graph()` runs without errors
4. Uncomment graph invocation in `main.py` CLI
5. Add Rich progress display using `graph.stream()`
6. Run end-to-end with a real resume and job URLs

### LangGraph concept: invoke vs stream

```python
# invoke() — run all nodes, return final state
final_state = graph.invoke(initial_state)

# stream() — yield state updates after each node (for progress display)
for event in graph.stream(initial_state):
    node_name = list(event.keys())[0]
    print(f"Completed: {node_name}")
```

### Common pitfalls

- **Infinite loop** — if `current_job_index` never advances
- **Pydantic vs dict** — LangGraph works with dicts internally; nodes return plain dicts
- **State merge** — if two nodes both update `jobs`, last one wins

### Debugging the graph

```python
graph = build_graph()
print(graph.get_graph().draw_ascii())  # visualize node/edge structure
```

## Alternatives Considered

- **Build the full pipeline with form filling first** — too risky; validate the graph structure before adding complexity

## Acceptance Criteria

- [ ] `build_graph()` compiles without errors
- [ ] `python -m apply_operator run --resume resume.pdf --urls urls.txt` executes the full pipeline
- [ ] All jobs are analyzed and scored
- [ ] High-fit jobs marked as "applied" (stub), low-fit jobs "skipped"
- [ ] Results saved to `data/results.json`
- [ ] Results table printed to console with Rich formatting
- [ ] No infinite loops — pipeline terminates for any input
- [ ] Integration test passes with mocked dependencies
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/fill_application.py` — stub implementation
- `src/apply_operator/nodes/report_results.py` — implement
- `src/apply_operator/main.py` — wire graph + progress display
- `src/apply_operator/graph.py` — verify, fix if needed
- `tests/test_graph.py` — create integration test

## Related Issues

- Blocked by [004](004-resume-structured-extraction.md), [006](006-search-jobs-node.md), [007](007-analyze-fit-node.md)
- Blocks [009](009-fill-application-node.md), [010](010-cli-progress-and-reporting.md), [011](011-error-handling-and-retry.md), [012](012-langgraph-checkpointing.md)
