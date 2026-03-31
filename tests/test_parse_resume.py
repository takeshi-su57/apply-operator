"""Tests for the parse_resume node."""

import json
from typing import Any
from unittest.mock import patch

from apply_operator.nodes.parse_resume import _strip_markdown_json, parse_resume
from apply_operator.state import ApplicationState, ResumeData

VALID_LLM_RESPONSE = json.dumps(
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-0100",
        "skills": ["Python", "TypeScript"],
        "experience": [
            {
                "title": "Senior Engineer",
                "company": "Acme Corp",
                "duration": "2020-2024",
                "description": "Led backend development",
            }
        ],
        "education": [{"degree": "BS Computer Science", "institution": "MIT", "year": "2020"}],
        "summary": "Experienced software engineer.",
    }
)


class TestStripMarkdownJson:
    def test_strips_json_code_fence(self) -> None:
        text = '```json\n{"name": "John"}\n```'
        assert _strip_markdown_json(text) == '{"name": "John"}'

    def test_strips_plain_code_fence(self) -> None:
        text = '```\n{"name": "John"}\n```'
        assert _strip_markdown_json(text) == '{"name": "John"}'

    def test_returns_plain_json_unchanged(self) -> None:
        text = '{"name": "John"}'
        assert _strip_markdown_json(text) == '{"name": "John"}'

    def test_strips_surrounding_whitespace(self) -> None:
        text = '  {"name": "John"}  '
        assert _strip_markdown_json(text) == '{"name": "John"}'


class TestParseResume:
    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_parses_valid_json_response(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "John Doe\njohn@example.com"
        mock_llm.return_value = VALID_LLM_RESPONSE

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert "resume" in result
        assert "errors" not in result
        resume: ResumeData = result["resume"]
        assert resume.name == "John Doe"
        assert resume.email == "john@example.com"
        assert resume.phone == "555-0100"
        assert resume.skills == ["Python", "TypeScript"]
        assert len(resume.experience) == 1
        assert len(resume.education) == 1
        assert resume.summary == "Experienced software engineer."
        assert resume.raw_text == "John Doe\njohn@example.com"

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_handles_invalid_json(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "some resume text"
        mock_llm.return_value = "not valid json at all"

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert result["resume"].raw_text == "some resume text"
        assert result["resume"].name == ""
        assert len(result["errors"]) == 1
        assert "Resume parse failed" in result["errors"][0]

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_handles_markdown_wrapped_json(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "John Doe\njohn@example.com"
        mock_llm.return_value = f"```json\n{VALID_LLM_RESPONSE}\n```"

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert "errors" not in result
        assert result["resume"].name == "John Doe"

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_handles_empty_resume_text(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = ""
        mock_llm.return_value = json.dumps({"name": "", "email": "", "skills": []})

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert result["resume"].raw_text == ""

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_handles_null_fields(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "Jane Doe\nSoftware Engineer"
        mock_llm.return_value = json.dumps(
            {
                "name": "Jane Doe",
                "email": None,
                "phone": None,
                "skills": ["Python"],
                "experience": None,
                "education": None,
                "summary": None,
            }
        )

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert "errors" not in result
        resume = result["resume"]
        assert resume.name == "Jane Doe"
        assert resume.email == ""
        assert resume.phone == ""
        assert resume.skills == ["Python"]
        assert resume.experience == []
        assert resume.education == []
        assert resume.summary == ""

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_handles_validation_error(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "some text"
        # skills should be a list, not a string — triggers ValidationError
        mock_llm.return_value = json.dumps({"skills": 12345})

        state = ApplicationState(resume_path="resume.pdf")
        result = parse_resume(state)

        assert result["resume"].raw_text == "some text"
        assert len(result["errors"]) == 1
        assert "Resume parse failed" in result["errors"][0]

    @patch("apply_operator.nodes.parse_resume.call_llm")
    @patch("apply_operator.nodes.parse_resume.extract_text")
    def test_preserves_existing_errors(self, mock_extract: Any, mock_llm: Any) -> None:
        mock_extract.return_value = "text"
        mock_llm.return_value = "bad json"

        state = ApplicationState(resume_path="resume.pdf", errors=["prior error"])
        result = parse_resume(state)

        assert result["errors"][0] == "prior error"
        assert "Resume parse failed" in result["errors"][1]
