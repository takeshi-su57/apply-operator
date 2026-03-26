# [Feature]: Implement analyze_fit node with LLM scoring

**Labels:** `enhancement`, `priority:high`
**Depends on:** [003](003-llm-provider-setup.md), [004](004-resume-structured-extraction.md)

## Description

Implement the `analyze_fit` node that uses the LLM to score how well the parsed resume matches the current job listing (0.0 to 1.0). The graph's conditional edges use this score to decide whether to apply (>= 0.6) or skip.

## Motivation

- Not every job is a good match — applying to irrelevant jobs wastes time and may hurt the user's reputation
- LLM-based scoring is more nuanced than keyword matching
- This node drives the graph's conditional routing (apply vs. skip)

## Proposed Solution

1. Get current job from `state.jobs[state.current_job_index]`
2. Build prompt with resume data + job description using `ANALYZE_FIT`
3. Call LLM, parse `{"score": 0.85, "reasoning": "..."}` response
4. Update the current job's `fit_score` and advance `current_job_index`

### Key challenge: updating a list item

```python
updated_jobs = list(state.jobs)
updated_jobs[idx] = state.jobs[idx].model_copy(update={"fit_score": score})
return {"jobs": updated_jobs, "current_job_index": idx + 1}
```

### Graph routing (already in graph.py)

- `fit_score >= 0.6` → `fill_application`
- `fit_score < 0.6` → skip (advance index, back to `analyze_fit`)
- `current_job_index >= len(jobs)` → `report_results`

**Important:** The index must advance in every path (apply AND skip) to prevent infinite loops.

## Alternatives Considered

- **Keyword matching** — fast but misses context (e.g., "Python" might mean snake care, not programming)
- **Embedding similarity** — more complex setup, requires vector DB; LLM scoring is simpler for v1

## Acceptance Criteria

- [ ] Node scores resume against job and stores `fit_score` in `JobListing`
- [ ] `current_job_index` advances correctly for both apply and skip paths
- [ ] Invalid LLM response (bad JSON) defaults to score 0.0 with error logged
- [ ] Score outside 0-1 range is clamped
- [ ] Out-of-bounds index returns immediately (no crash)
- [ ] Tests pass with mocked LLM
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/analyze_fit.py` — implement
- `src/apply_operator/prompts/job_matching.py` — refine `ANALYZE_FIT` if needed
- `src/apply_operator/graph.py` — verify index advancement logic
- `tests/test_analyze_fit.py` — create

## Related Issues

- Blocked by [003](003-llm-provider-setup.md) and [004](004-resume-structured-extraction.md)
- Blocks [008](008-minimal-graph-integration.md)
