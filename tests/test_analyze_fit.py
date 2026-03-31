"""Tests for the analyze_fit node."""

from typing import Any
from unittest.mock import patch

from apply_operator.nodes.analyze_fit import analyze_fit
from apply_operator.state import ApplicationState, JobListing, ResumeData


class TestAnalyzeFit:
    """Tests for analyze_fit node function."""

    def _make_state(
        self,
        jobs: list[JobListing] | None = None,
        current_job_index: int = 0,
        errors: list[str] | None = None,
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
            summary="Experienced backend developer.",
        )
        if jobs is None:
            jobs = [
                JobListing(
                    url="https://example.com/jobs/1",
                    title="Python Developer",
                    company="TechCo",
                    description="Looking for a Python developer with Django experience.",
                ),
            ]
        return {
            "resume": resume,
            "jobs": jobs,
            "current_job_index": current_job_index,
            "errors": errors or [],
            "resume_path": "",
            "job_urls": [],
            "total_applied": 0,
            "total_skipped": 0,
        }

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_scores_job_with_valid_response(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": 0.85, "reasoning": "Strong Python match"}'
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.85
        assert "errors" not in result

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_does_not_advance_index(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": 0.85, "reasoning": "Good match"}'
        state = self._make_state()

        result = analyze_fit(state)

        assert "current_job_index" not in result

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_clamps_score_above_one(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": 1.5, "reasoning": "Off the charts"}'
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 1.0

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_clamps_score_below_zero(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": -0.3, "reasoning": "Terrible fit"}'
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.0

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_invalid_json_defaults_to_zero(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = "This is not JSON at all"
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.0
        assert any("Fit analysis failed" in e for e in result["errors"])

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_missing_score_field_defaults_to_zero(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"reasoning": "No score provided"}'
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.0

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_markdown_wrapped_json(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '```json\n{"score": 0.7, "reasoning": "Good"}\n```'
        state = self._make_state()

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.7

    def test_out_of_bounds_index_returns_empty(self) -> None:
        state = self._make_state(current_job_index=5)

        result = analyze_fit(state)

        assert result == {}

    def test_empty_jobs_list_returns_empty(self) -> None:
        state = self._make_state(jobs=[], current_job_index=0)

        result = analyze_fit(state)

        assert result == {}

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_scores_correct_job_by_index(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": 0.9, "reasoning": "Great"}'
        jobs = [
            JobListing(url="https://example.com/1", title="Job A", company="Co A"),
            JobListing(url="https://example.com/2", title="Job B", company="Co B"),
        ]
        state = self._make_state(jobs=jobs, current_job_index=1)

        result = analyze_fit(state)

        assert result["jobs"][0].fit_score == 0.0  # unchanged
        assert result["jobs"][1].fit_score == 0.9  # scored

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_returns_only_new_errors(self, mock_call_llm: Any) -> None:
        """With the reducer, nodes return only new errors (framework accumulates)."""
        mock_call_llm.return_value = "not json"
        state = self._make_state()

        result = analyze_fit(state)

        assert len(result["errors"]) == 1
        assert "Fit analysis failed" in result["errors"][0]

    @patch("apply_operator.nodes.analyze_fit.call_llm")
    def test_prompt_includes_resume_and_job_data(self, mock_call_llm: Any) -> None:
        mock_call_llm.return_value = '{"score": 0.5, "reasoning": "OK"}'
        state = self._make_state()

        analyze_fit(state)

        prompt = mock_call_llm.call_args[0][0]
        assert "Jane Smith" in prompt
        assert "Python" in prompt
        assert "TechCo" in prompt
        assert "Python Developer" in prompt


class TestSkipJob:
    """Tests for the skip_job graph helper."""

    def test_advances_index_and_increments_skipped(self) -> None:
        from apply_operator.graph import skip_job

        state: ApplicationState = {
            "jobs": [
                JobListing(url="https://example.com/1", fit_score=0.3),
                JobListing(url="https://example.com/2"),
            ],
            "current_job_index": 0,
            "total_skipped": 0,
        }

        result = skip_job(state)

        assert result["current_job_index"] == 1
        assert result["total_skipped"] == 1


class TestShouldApply:
    """Tests for the should_apply routing function."""

    def test_routes_apply_for_high_score(self) -> None:
        from apply_operator.graph import should_apply

        state: ApplicationState = {
            "jobs": [JobListing(url="https://example.com/1", fit_score=0.8)],
            "current_job_index": 0,
        }

        assert should_apply(state) == "apply"

    def test_routes_skip_for_low_score(self) -> None:
        from apply_operator.graph import should_apply

        state: ApplicationState = {
            "jobs": [JobListing(url="https://example.com/1", fit_score=0.3)],
            "current_job_index": 0,
        }

        assert should_apply(state) == "skip"

    def test_routes_apply_at_threshold(self) -> None:
        from apply_operator.graph import should_apply

        state: ApplicationState = {
            "jobs": [JobListing(url="https://example.com/1", fit_score=0.6)],
            "current_job_index": 0,
        }

        assert should_apply(state) == "apply"

    def test_routes_report_when_all_processed(self) -> None:
        from apply_operator.graph import should_apply

        state: ApplicationState = {
            "jobs": [JobListing(url="https://example.com/1", fit_score=0.8)],
            "current_job_index": 1,
        }

        assert should_apply(state) == "report"

    def test_routes_report_for_empty_jobs(self) -> None:
        from apply_operator.graph import should_apply

        state: ApplicationState = {"jobs": [], "current_job_index": 0}

        assert should_apply(state) == "report"
