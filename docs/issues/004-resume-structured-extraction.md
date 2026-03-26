# [Feature]: Implement parse_resume node (first LangGraph node)

**Labels:** `enhancement`, `priority:high`
**Status:** Done
**Depends on:** [002](002-pdf-text-extraction.md), [003](003-llm-provider-setup.md)

## Description

Implement the `parse_resume` node — the first LangGraph node in the pipeline. It extracts raw text from the PDF (issue 002) and uses the LLM (issue 003) to parse it into structured `ResumeData` (name, email, skills, experience, etc.).

## Motivation

- This is the entry point of the agent pipeline — all downstream nodes depend on structured resume data
- First opportunity to learn the LangGraph node pattern: `(state) -> dict`
- Validates that state flows correctly through the graph

## Implementation

1. Call `extract_text(state.resume_path)` for raw text
2. Format the `PARSE_RESUME` prompt with the raw text
3. Call `call_llm(prompt)` and parse the JSON response
4. Strip markdown code fences (```json ... ```) if present via `_strip_markdown_json()`
5. Return `{"resume": ResumeData(...)}` for LangGraph to merge into state
6. On parse failure, return fallback `ResumeData(raw_text=...)` with error appended

### Key pattern (LangGraph node)

```python
def parse_resume(state: ApplicationState) -> dict[str, Any]:
    raw_text = extract_text(state.resume_path)
    prompt = PARSE_RESUME.format(resume_text=raw_text)
    try:
        response = call_llm(prompt)
        cleaned = _strip_markdown_json(response)
        data = json.loads(cleaned)
        resume = ResumeData(raw_text=raw_text, **data)
    except (json.JSONDecodeError, ValidationError) as e:
        resume = ResumeData(raw_text=raw_text)
        return {"resume": resume, "errors": [*state.errors, f"Resume parse failed: {e}"]}
    return {"resume": resume}
```

### Additional changes

- **`ResumeData` null coercion** — Added a `model_validator` on `ResumeData` that coerces
  `None` values to defaults (empty string, empty list). LLMs return `null` for missing
  fields like phone number; without coercion Pydantic rejects them.
- **`llm_max_tokens` config** — Added configurable `LLM_MAX_TOKENS` env var (default 8192)
  passed to all LLM providers. Ensures long resumes with many experiences don't get
  truncated by low default token limits.
- **LLM call logging** — `call_llm()` logs provider, model, and execution time at INFO
  level for model performance comparison.
- **CLI Rich table** — `parse-resume` command displays structured data as a Rich table
  with experience details and sentence counts.

### LangGraph concept: state updates

When a node returns `{"resume": resume}`, LangGraph only updates that field — all other fields stay unchanged.

## Alternatives Considered

- **Regex-based parsing** — fragile, breaks on different resume formats
- **Dedicated resume parser libraries** — exist but less flexible than LLM extraction

## Acceptance Criteria

- [x] `parse_resume` node correctly extracts name, email, skills from a real resume PDF
- [x] Invalid LLM responses (bad JSON) don't crash — fall back to `ResumeData(raw_text=...)`
- [x] Markdown-wrapped JSON responses (```json ... ```) are handled
- [x] `parse-resume` CLI command shows structured data as a Rich table
- [x] Tests pass with mocked `extract_text` and `call_llm`
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/parse_resume.py` — implemented node with `_strip_markdown_json` helper
- `src/apply_operator/prompts/resume_analysis.py` — refined prompt, escaped braces, added null instruction
- `src/apply_operator/main.py` — Rich table output with experience details, logging setup
- `src/apply_operator/state.py` — `ResumeData` null coercion `model_validator`
- `src/apply_operator/config.py` — added `llm_max_tokens` setting
- `src/apply_operator/tools/llm_provider.py` — `max_tokens` support, execution time logging
- `tests/test_parse_resume.py` — 11 tests (strip markdown, valid/invalid JSON, null fields, validation errors)

## Related Issues

- Blocked by [002](002-pdf-text-extraction.md) and [003](003-llm-provider-setup.md)
- Blocks [008](008-minimal-graph-integration.md)
