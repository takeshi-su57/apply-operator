# Testing Rules

## Current State

Tests are minimal stubs. This document establishes standards as tests are added.

## Testing Strategy

| Layer | Target | Tool | Priority |
|-------|--------|------|----------|
| Unit | Tools (`tools/*.py`) | pytest | High |
| Unit | State models (`state.py`) | pytest | High |
| Unit | Node functions (`nodes/*.py`) | pytest (mocked tools) | Medium |
| Integration | Graph execution (`graph.py`) | pytest (mocked tools) | Medium |
| E2E | Full pipeline with real browser | pytest + pytest-asyncio | Low |

## File Conventions

- Tests live in `tests/` directory
- Naming: `test_<module>.py` (e.g., `test_pdf_parser.py`, `test_analyze_fit.py`)
- Shared fixtures in `tests/conftest.py`
- Test naming:
  ```python
  class TestPdfParser:
      def test_extracts_text_from_valid_pdf(self) -> None: ...
      def test_raises_on_missing_file(self) -> None: ...
  ```

## What to Test First (Priority Order)

1. **`state.py`** — Pydantic models with defaults (easiest, pure data)
2. **`tools/pdf_parser.py`** — Pure text extraction (mock file I/O)
3. **`tools/llm_provider.py`** — Factory returns correct provider type
4. **`nodes/*.py`** — Each node with mocked tools (LLM, browser)
5. **`graph.py`** — Graph assembly and routing logic

## Mocking Patterns

### Mock LLM calls
```python
from unittest.mock import patch, MagicMock

@patch("apply_operator.tools.llm_provider.get_llm")
def test_analyze_fit(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = '{"score": 0.8, "reasoning": "Good match"}'
    mock_get_llm.return_value = mock_llm
    # ... call node function
```

### Mock Playwright browser
```python
from unittest.mock import AsyncMock, patch

@patch("apply_operator.tools.browser.get_page")
async def test_search_jobs(mock_get_page):
    mock_page = AsyncMock()
    mock_page.content.return_value = "<html>...</html>"
    mock_get_page.return_value.__aenter__.return_value = mock_page
    # ... call node function
```

### Mock environment variables
```python
@patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
def test_config_loads():
    settings = Settings()
    assert settings.llm_provider == "openai"
```

## Fixtures (in conftest.py)

- `sample_resume` — Pre-built `ResumeData` with realistic test data
- `sample_jobs` — List of `JobListing` objects
- `sample_state` — Full `ApplicationState` with resume + jobs

## Coverage Targets

- **Tools:** 90%+ line coverage
- **Nodes:** 80%+ line coverage (with mocked tools)
- **State models:** 100% (constructors, defaults, validation)
- **Graph routing:** 80%+ (test conditional edge logic)

## Rules

- Test the public interface, not implementation details
- Each test should have a single assertion focus
- Use descriptive test names that explain expected behavior
- Always mock external I/O (LLM calls, browser, file system)
- Do not test LLM output quality — test that the node correctly processes LLM responses
- Do not snapshot test LLM responses — they are non-deterministic
