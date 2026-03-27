# [Feature]: Implement analyze_fit node with LLM scoring

**Labels:** `enhancement`, `priority:high`
**Depends on:** [003](003-llm-provider-setup.md), [004](004-resume-structured-extraction.md)

## Description

Implement the `analyze_fit` node that uses the LLM to score how well the parsed resume matches the current job listing (0.0 to 1.0). The graph's conditional edges use this score to decide whether to apply (>= 0.6) or skip.

## Motivation

- Not every job is a good match — applying to irrelevant jobs wastes time and may hurt the user's reputation
- LLM-based scoring is more nuanced than keyword matching
- This node drives the graph's conditional routing (apply vs. skip)

## Implementation

### analyze_fit node (`nodes/analyze_fit.py`)

1. Get current job from `state.jobs[state.current_job_index]`
2. Build prompt with resume data + job description using `ANALYZE_FIT` template
3. Call LLM via `call_llm()`, parse `{"score": 0.85, "reasoning": "..."}` JSON response
4. Clamp score to 0.0–1.0 range
5. Update the current job's `fit_score` — does **not** advance `current_job_index`

```python
updated_jobs = list(state.jobs)
updated_jobs[idx] = job.model_copy(update={"fit_score": score})
return {"jobs": updated_jobs}
```

On invalid JSON: defaults to score 0.0 and appends error to `state.errors`.

### Graph routing fix (`graph.py`)

The original design had `analyze_fit` advancing `current_job_index` and the `"skip"` edge looping back to `analyze_fit`. This caused `should_apply` to check the **next** (unscored) job instead of the just-scored one, making the "apply" path unreachable.

**Fix:** `analyze_fit` only scores (no index advancement). A new `skip_job` node handles index advancement and skip counting for the low-score path.

```
analyze_fit → should_apply →
  "apply"  → fill_application → has_more_jobs → analyze_fit or report_results
  "skip"   → skip_job → analyze_fit
  "report" → report_results
```

### Additional fixes discovered during implementation

- **`main.py` _print_results crash** — used `.get()` (dict API) on `JobListing` Pydantic objects returned by LangGraph. Fixed to handle both dicts and Pydantic objects.
- **`browser.py` stale tests (11 failures)** — `test_browser.py` and `test_search_jobs.py` had tests written against a removed `_get_browser_headed` API, old JSON session storage, and outdated call signatures. All 11 tests updated to match current production code.
- **Page rendering race condition** — job sites with JS-rendered content (skeleton screens, lazy-loaded lists) returned 0 jobs because content extraction happened before rendering completed. Added `wait_for_page_ready()` helper that waits for network idle + content stability.
- **Logging framework** — added `@log_node` decorator for consistent node entry/exit/duration logging, and `purpose=` parameter to `call_llm()` for contextual LLM call logs. Created `.claude/rules/logging.md` to codify conventions.

## Alternatives Considered

- **Keyword matching** — fast but misses context (e.g., "Python" might mean snake care, not programming)
- **Embedding similarity** — more complex setup, requires vector DB; LLM scoring is simpler for v1
- **Index advancement in analyze_fit** — original design; caused routing bug where `should_apply` always saw unscored jobs

## Acceptance Criteria

- [x] Node scores resume against job and stores `fit_score` in `JobListing`
- [x] `current_job_index` advances correctly for both apply and skip paths
- [x] Invalid LLM response (bad JSON) defaults to score 0.0 with error logged
- [x] Score outside 0-1 range is clamped
- [x] Out-of-bounds index returns immediately (no crash)
- [x] Tests pass with mocked LLM (18 tests for analyze_fit + routing)
- [x] `ruff check` and `mypy` pass
- [x] All 81 tests pass (including fixed pre-existing failures)

## Files Touched

- `src/apply_operator/nodes/analyze_fit.py` — full implementation with LLM scoring
- `src/apply_operator/graph.py` — added `skip_job` node, fixed routing logic
- `src/apply_operator/main.py` — fixed `_print_results` Pydantic object handling
- `src/apply_operator/tools/browser.py` — added `wait_for_page_ready()`, removed unused import
- `src/apply_operator/tools/llm_provider.py` — added `purpose=` parameter to `call_llm()`
- `src/apply_operator/tools/logging_utils.py` — new `@log_node` decorator
- `src/apply_operator/nodes/parse_resume.py` — added `@log_node`, `purpose=`
- `src/apply_operator/nodes/search_jobs.py` — added `@log_node`, `purpose=`, `wait_for_page_ready()`
- `src/apply_operator/nodes/fill_application.py` — added `@log_node`
- `src/apply_operator/nodes/report_results.py` — added `@log_node`, result summary logging
- `.claude/CLAUDE.md` — added logging rule reference
- `.claude/rules/logging.md` — new logging conventions rule
- `tests/test_analyze_fit.py` — new (18 tests)
- `tests/test_browser.py` — fixed 10 stale tests
- `tests/test_search_jobs.py` — fixed 1 stale test

## Related Issues

- Blocked by [003](003-llm-provider-setup.md) and [004](004-resume-structured-extraction.md)
- Blocks [008](008-minimal-graph-integration.md)
