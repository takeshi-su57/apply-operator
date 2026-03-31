"""Tests for the generate_cover_letter node."""

from typing import Any
from unittest.mock import patch

from apply_operator.nodes.generate_cover_letter import generate_cover_letter
from apply_operator.state import ApplicationState, JobListing, ResumeData


def _make_state(
    jobs: list[JobListing] | None = None,
    current_job_index: int = 0,
) -> ApplicationState:
    resume = ResumeData(
        raw_text="Jane Smith\nPython Developer",
        name="Jane Smith",
        skills=["Python", "Django", "PostgreSQL"],
        experience=[
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "duration": "2021-2024",
                "description": "Built APIs",
            }
        ],
        summary="Experienced backend developer with 3+ years in Python.",
    )
    if jobs is None:
        jobs = [
            JobListing(
                url="https://example.com/jobs/1",
                title="Python Developer",
                company="TechCo",
                description="Looking for a Python developer with Django experience.",
                fit_score=0.8,
            ),
        ]
    return {
        "resume": resume,
        "jobs": jobs,
        "current_job_index": current_job_index,
        "errors": [],
        "resume_path": "",
        "job_urls": [],
        "total_applied": 0,
        "total_skipped": 0,
    }


class TestGenerateCoverLetter:
    """Tests for generate_cover_letter node function."""

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_generates_cover_letter(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"cover_letter": "Dear Hiring Manager, ..."}'
        state = _make_state()

        result = generate_cover_letter(state)

        assert result["jobs"][0].cover_letter == "Dear Hiring Manager, ..."
        assert "errors" not in result

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_handles_invalid_json(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = "not valid json"
        state = _make_state()

        result = generate_cover_letter(state)

        assert result["jobs"][0].cover_letter == ""
        assert len(result["errors"]) == 1
        assert "Cover letter generation failed" in result["errors"][0]

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_handles_missing_cover_letter_key(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"something_else": "value"}'
        state = _make_state()

        result = generate_cover_letter(state)

        assert result["jobs"][0].cover_letter == ""
        assert "errors" not in result

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_handles_markdown_wrapped_json(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '```json\n{"cover_letter": "Dear TechCo team, ..."}\n```'
        state = _make_state()

        result = generate_cover_letter(state)

        assert result["jobs"][0].cover_letter == "Dear TechCo team, ..."

    def test_out_of_bounds_index_returns_empty(self) -> None:
        state = _make_state(current_job_index=5)

        result = generate_cover_letter(state)

        assert result == {}

    def test_empty_jobs_list_returns_empty(self) -> None:
        state = _make_state(jobs=[], current_job_index=0)

        result = generate_cover_letter(state)

        assert result == {}

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_does_not_advance_index(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"cover_letter": "Dear ..."}'
        state = _make_state()

        result = generate_cover_letter(state)

        assert "current_job_index" not in result

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_updates_correct_job_by_index(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"cover_letter": "For Job B"}'
        jobs = [
            JobListing(url="https://example.com/1", title="Job A", fit_score=0.8),
            JobListing(url="https://example.com/2", title="Job B", fit_score=0.9),
        ]
        state = _make_state(jobs=jobs, current_job_index=1)

        result = generate_cover_letter(state)

        assert result["jobs"][0].cover_letter == ""  # unchanged
        assert result["jobs"][1].cover_letter == "For Job B"

    @patch("apply_operator.nodes.generate_cover_letter.call_llm")
    def test_prompt_includes_resume_and_job_data(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"cover_letter": "..."}'
        state = _make_state()

        generate_cover_letter(state)

        prompt = mock_call_llm.call_args[0][0]
        assert "Jane Smith" in prompt
        assert "Python" in prompt
        assert "TechCo" in prompt
        assert "Python Developer" in prompt
