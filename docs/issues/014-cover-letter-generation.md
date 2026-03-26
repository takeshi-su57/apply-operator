# [Feature]: Add cover letter generation node

**Labels:** `enhancement`, `priority:low`
**Depends on:** [007](007-analyze-fit-node.md)

## Description

Add an optional `generate_cover_letter` node that creates a tailored cover letter for high-fit jobs. Runs after `analyze_fit` (for jobs with fit >= 0.6 only) and before `fill_application`.

## Motivation

- Many job applications require or benefit from a personalized cover letter
- LLM can generate one tailored to the specific job and resume
- Only runs for high-fit jobs, so it doesn't waste LLM calls on skipped positions

## Proposed Solution

- Create `nodes/generate_cover_letter.py` with prompt + LLM call
- Add `cover_letter: str` field to `ApplicationState`
- Wire into graph: `analyze_fit → [fit >= 0.6] → generate_cover_letter → fill_application`
- Update `fill_application` to include cover letter in form data

## Alternatives Considered

- **Static cover letter** — user provides one cover letter, used for all jobs. Simpler but not personalized.
- **No cover letter** — some applications don't require one, but it improves response rates

## Acceptance Criteria

- [ ] Cover letter generated for high-fit jobs only
- [ ] Cover letter mentions company name and relevant skills
- [ ] Cover letter used in `fill_application` if form has a cover letter field
- [ ] Low-fit jobs skip cover letter generation
- [ ] Tests pass with mocked LLM
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/generate_cover_letter.py` — create
- `src/apply_operator/nodes/__init__.py` — add export
- `src/apply_operator/prompts/cover_letter.py` — create
- `src/apply_operator/state.py` — add `cover_letter` field
- `src/apply_operator/graph.py` — insert node in graph
- `tests/test_generate_cover_letter.py` — create

## Related Issues

- Blocked by [007](007-analyze-fit-node.md)
