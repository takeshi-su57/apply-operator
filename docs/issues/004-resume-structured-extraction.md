# [Feature]: Implement parse_resume node (first LangGraph node)

**Labels:** `enhancement`, `priority:high`
**Depends on:** [002](002-pdf-text-extraction.md), [003](003-llm-provider-setup.md)

## Description

Implement the `parse_resume` node — the first LangGraph node in the pipeline. It extracts raw text from the PDF (issue 002) and uses the LLM (issue 003) to parse it into structured `ResumeData` (name, email, skills, experience, etc.).

## Motivation

- This is the entry point of the agent pipeline — all downstream nodes depend on structured resume data
- First opportunity to learn the LangGraph node pattern: `(state) -> dict`
- Validates that state flows correctly through the graph

## Proposed Solution

1. Call `extract_text(state.resume_path)` for raw text
2. Format the `PARSE_RESUME` prompt with the raw text
3. Call `call_llm(prompt)` and parse the JSON response
4. Return `{"resume": ResumeData(...)}` for LangGraph to merge into state

### Key pattern (LangGraph node)

```python
def parse_resume(state: ApplicationState) -> dict:
    raw_text = extract_text(state.resume_path)
    prompt = PARSE_RESUME.format(resume_text=raw_text)
    response = call_llm(prompt)
    try:
        data = json.loads(response)
        resume = ResumeData(raw_text=raw_text, **data)
    except (json.JSONDecodeError, ValueError) as e:
        resume = ResumeData(raw_text=raw_text)
        return {"resume": resume, "errors": [*state.errors, f"Resume parse failed: {e}"]}
    return {"resume": resume}
```

### LangGraph concept: state updates

When a node returns `{"resume": resume}`, LangGraph only updates that field — all other fields stay unchanged.

## Alternatives Considered

- **Regex-based parsing** — fragile, breaks on different resume formats
- **Dedicated resume parser libraries** — exist but less flexible than LLM extraction

## Acceptance Criteria

- [ ] `parse_resume` node correctly extracts name, email, skills from a real resume PDF
- [ ] Invalid LLM responses (bad JSON) don't crash — fall back to `ResumeData(raw_text=...)`
- [ ] Markdown-wrapped JSON responses (```json ... ```) are handled
- [ ] `parse-resume` CLI command shows structured data as a Rich table
- [ ] Tests pass with mocked `extract_text` and `call_llm`
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/parse_resume.py` — implement
- `src/apply_operator/prompts/resume_analysis.py` — refine prompt if needed
- `src/apply_operator/main.py` — update `parse-resume` command output
- `tests/test_parse_resume.py` — create

## Related Issues

- Blocked by [002](002-pdf-text-extraction.md) and [003](003-llm-provider-setup.md)
- Blocks [008](008-minimal-graph-integration.md)
