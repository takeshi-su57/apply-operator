# [Feature]: Add cover letter generation node

**Labels:** `enhancement`, `priority:low`
**Depends on:** [007](007-analyze-fit-node.md)

## Description

Add a `generate_cover_letter` node that creates a tailored cover letter for high-fit jobs. Runs after `analyze_fit` (for jobs with fit >= 0.6 only) and before `fill_application`.

## Motivation

- Many job applications require or benefit from a personalized cover letter
- LLM can generate one tailored to the specific job and resume
- Only runs for high-fit jobs, so it doesn't waste LLM calls on skipped positions

## Implementation

### New node: `generate_cover_letter`

Located at `src/apply_operator/nodes/generate_cover_letter.py`. Follows the same pattern as `analyze_fit`:
- Uses `@log_node` decorator
- Reads current job and resume from state via dict access
- Calls `call_llm()` with the `GENERATE_COVER_LETTER` prompt
- Stores the generated cover letter on `JobListing.cover_letter` via `model_copy()`
- Returns `{"jobs": updated_jobs}` (and `{"errors": [...]}` on failure)

### Graph flow change

```
analyze_fit → [fit >= 0.6] → generate_cover_letter → fill_application
```

The new node is inserted between `analyze_fit` and `fill_application`. Low-fit jobs skip both `generate_cover_letter` and `fill_application`.

### Cover letter in form filling

`fill_application._map_fields_with_llm()` now passes `job.cover_letter` to the `MAP_FORM_FIELDS` prompt. If a form field asks for a cover letter, the LLM uses the pre-generated one instead of composing inline.

### State change

Added `cover_letter: str = ""` field to `JobListing` model.

## Alternatives Considered

- **Static cover letter** -- user provides one, used for all jobs. Simpler but not personalized.
- **Inline generation in fill_application** -- was the previous workaround (2-3 sentence answer composed per form field). The dedicated node generates a proper multi-paragraph letter once.

## Acceptance Criteria

- [x] Cover letter generated for high-fit jobs only
- [x] Cover letter mentions company name and relevant skills (via prompt)
- [x] Cover letter used in `fill_application` if form has a cover letter field
- [x] Low-fit jobs skip cover letter generation
- [x] Tests pass with mocked LLM (9 new tests)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/generate_cover_letter.py` -- **new**: cover letter node
- `src/apply_operator/prompts/cover_letter.py` -- **new**: `GENERATE_COVER_LETTER` prompt
- `src/apply_operator/nodes/__init__.py` -- added export
- `src/apply_operator/state.py` -- added `cover_letter` field to `JobListing`
- `src/apply_operator/graph.py` -- inserted node in graph flow
- `src/apply_operator/nodes/fill_application.py` -- passes cover letter to form mapping prompt
- `src/apply_operator/prompts/form_filling.py` -- updated `MAP_FORM_FIELDS` to use pre-generated cover letter
- `tests/test_generate_cover_letter.py` -- **new**: 9 tests
- `tests/test_graph.py` -- added mock and expected node name
- `tests/test_checkpoint.py` -- added mock to all patched graphs

## Related Issues

- Blocked by [007](007-analyze-fit-node.md)
