"""Tests for state model definitions."""

from typing import get_type_hints

from apply_operator.state import ApplicationState, JobListing, ResumeData


class TestResumeData:
    """Tests for ResumeData Pydantic model."""

    def test_default_values(self) -> None:
        resume = ResumeData()
        assert resume.raw_text == ""
        assert resume.name == ""
        assert resume.email == ""
        assert resume.phone == ""
        assert resume.skills == []
        assert resume.experience == []
        assert resume.education == []
        assert resume.summary == ""

    def test_coerce_none_to_defaults(self) -> None:
        """None values should be replaced with field defaults."""
        resume = ResumeData(
            name=None,  # type: ignore[arg-type]
            email=None,  # type: ignore[arg-type]
            phone=None,  # type: ignore[arg-type]
            skills=None,  # type: ignore[arg-type]
            experience=None,  # type: ignore[arg-type]
            education=None,  # type: ignore[arg-type]
            summary=None,  # type: ignore[arg-type]
        )
        assert resume.name == ""
        assert resume.email == ""
        assert resume.phone == ""
        assert resume.skills == []
        assert resume.experience == []
        assert resume.education == []
        assert resume.summary == ""

    def test_coerce_none_preserves_non_none_values(self) -> None:
        resume = ResumeData(
            name="Jane",
            skills=["Python"],
            summary=None,  # type: ignore[arg-type]
        )
        assert resume.name == "Jane"
        assert resume.skills == ["Python"]
        assert resume.summary == ""

    def test_with_full_data(self) -> None:
        resume = ResumeData(
            raw_text="full text",
            name="John Doe",
            email="john@example.com",
            phone="555-0100",
            skills=["Python", "Go"],
            experience=[{"title": "Dev", "company": "Acme"}],
            education=[{"degree": "BS", "institution": "MIT"}],
            summary="Experienced engineer.",
        )
        assert resume.name == "John Doe"
        assert len(resume.skills) == 2
        assert len(resume.experience) == 1
        assert len(resume.education) == 1


class TestJobListing:
    """Tests for JobListing Pydantic model."""

    def test_required_url(self) -> None:
        job = JobListing(url="https://example.com/jobs/1")
        assert job.url == "https://example.com/jobs/1"

    def test_default_values(self) -> None:
        job = JobListing(url="https://example.com")
        assert job.title == ""
        assert job.company == ""
        assert job.description == ""
        assert job.location == ""
        assert job.fit_score == 0.0
        assert job.applied is False
        assert job.cover_letter == ""
        assert job.error == ""

    def test_model_copy_update(self) -> None:
        job = JobListing(url="https://example.com", title="Dev")
        updated = job.model_copy(update={"fit_score": 0.9, "applied": True})
        assert updated.fit_score == 0.9
        assert updated.applied is True
        assert updated.title == "Dev"  # unchanged

    def test_model_dump(self) -> None:
        job = JobListing(url="https://example.com", title="Dev", company="Acme")
        data = job.model_dump()
        assert data["url"] == "https://example.com"
        assert data["title"] == "Dev"
        assert data["company"] == "Acme"
        assert "cover_letter" in data


class TestApplicationState:
    """Tests for ApplicationState TypedDict."""

    def test_is_typed_dict(self) -> None:
        hints = get_type_hints(ApplicationState, include_extras=True)
        assert "resume_path" in hints
        assert "job_urls" in hints
        assert "resume" in hints
        assert "jobs" in hints
        assert "current_job_index" in hints
        assert "total_applied" in hints
        assert "total_skipped" in hints
        assert "errors" in hints

    def test_can_create_as_dict(self) -> None:
        state: ApplicationState = {
            "resume_path": "test.pdf",
            "job_urls": ["https://example.com"],
            "errors": [],
        }
        assert state["resume_path"] == "test.pdf"
        assert len(state["job_urls"]) == 1

    def test_total_false_allows_partial(self) -> None:
        """TypedDict(total=False) means all keys are optional at type level."""
        state: ApplicationState = {"resume_path": "test.pdf"}
        assert state["resume_path"] == "test.pdf"
