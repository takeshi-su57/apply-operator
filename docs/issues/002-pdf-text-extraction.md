# [Feature]: Implement PDF text extraction tool

**Labels:** `enhancement`, `priority:high`, `good first issue`
**Depends on:** [001](001-project-setup-and-verify.md)

## Description

Implement `tools/pdf_parser.py` to extract raw text from a resume PDF file using PyMuPDF. This is pure text extraction — no LLM involved.

## Motivation

- Resume parsing is the first step in the agent pipeline
- PDF text extraction is the simplest tool to implement (no external API calls)
- Good first feature to get comfortable with the codebase before tackling LLM or browser code

## Proposed Solution

- Implement `extract_text(pdf_path: str) -> str` using PyMuPDF (`fitz`)
- Open PDF, iterate pages, concatenate text with newlines
- Wire into the `parse-resume` CLI command to display extracted text
- Create a test PDF fixture programmatically for automated tests

### Key code example

```python
import fitz

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
```

### Test fixture example

```python
@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "resume.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "John Doe\njohn@example.com\nPython Developer")
    doc.save(str(path))
    doc.close()
    return path
```

## Alternatives Considered

- **pdfplumber** — better for tables but ~50x slower than PyMuPDF for plain text
- **pypdf** — pure Python (no C dependency) but slower and less accurate layout

## Acceptance Criteria

- [ ] `extract_text()` returns text content from a valid PDF
- [ ] `FileNotFoundError` raised for missing path
- [ ] Empty string returned for PDF with no text
- [ ] `python -m apply_operator parse-resume --resume sample.pdf` prints extracted text
- [ ] Tests pass: valid PDF, missing file, empty PDF
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/pdf_parser.py` — implement
- `src/apply_operator/main.py` — wire `parse-resume` command
- `tests/test_pdf_parser.py` — rewrite with real tests
- `tests/conftest.py` — add PDF fixture

## Related Issues

- Blocks [004](004-resume-structured-extraction.md) (needs raw text before LLM parsing)
