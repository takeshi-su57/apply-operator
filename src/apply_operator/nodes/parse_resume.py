"""Node: Parse resume PDF and extract structured data."""

from typing import Any

from apply_operator.state import ApplicationState


def parse_resume(state: ApplicationState) -> dict[str, Any]:
    """Extract text from resume PDF and parse into structured fields.

    Uses PyMuPDF for text extraction, then LLM for structured parsing.
    """
    # TODO: Implement
    # 1. Extract raw text with pdf_parser.extract_text(state.resume_path)
    # 2. Use LLM to parse into ResumeData fields
    # 3. Return {"resume": ResumeData(...)}
    return {}
