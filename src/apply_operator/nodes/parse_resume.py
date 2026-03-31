"""Node: Parse resume PDF and extract structured data."""

import json
import re
from typing import Any

from pydantic import ValidationError

from apply_operator.prompts.resume_analysis import PARSE_RESUME
from apply_operator.state import ApplicationState, ResumeData
from apply_operator.tools.llm_provider import call_llm
from apply_operator.tools.logging_utils import log_node
from apply_operator.tools.pdf_parser import extract_text
from apply_operator.tools.retry import FatalConfigError


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


@log_node
def parse_resume(state: ApplicationState) -> dict[str, Any]:
    """Extract text from resume PDF and parse into structured fields.

    Uses PyMuPDF for text extraction, then LLM for structured parsing.
    """
    raw_text = extract_text(state.resume_path)
    prompt = PARSE_RESUME.format(resume_text=raw_text)

    try:
        response = call_llm(prompt, purpose="parse_resume", expect_json=True)
        cleaned = _strip_markdown_json(response)

        data = json.loads(cleaned)
        resume = ResumeData(raw_text=raw_text, **data)
    except FatalConfigError:
        raise
    except (json.JSONDecodeError, ValidationError) as e:
        resume = ResumeData(raw_text=raw_text)
        return {"resume": resume, "errors": [*state.errors, f"Resume parse failed: {e}"]}
    return {"resume": resume}
