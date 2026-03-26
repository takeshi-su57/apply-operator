"""Shared test fixtures for apply-operator."""

import pytest

from apply_operator.state import ApplicationState, JobListing, ResumeData


@pytest.fixture
def sample_resume() -> ResumeData:
    """Sample parsed resume data for testing."""
    return ResumeData(
        raw_text="John Doe\njohn@example.com\nSoftware Engineer...",
        name="John Doe",
        email="john@example.com",
        phone="555-0100",
        skills=["Python", "TypeScript", "React", "PostgreSQL"],
        experience=[
            {
                "title": "Senior Engineer",
                "company": "Acme Corp",
                "duration": "2020-2024",
                "description": "Led backend development",
            }
        ],
        education=[
            {
                "degree": "BS Computer Science",
                "institution": "MIT",
                "year": "2020",
            }
        ],
        summary="Experienced software engineer with 4 years in backend development.",
    )


@pytest.fixture
def sample_jobs() -> list[JobListing]:
    """Sample job listings for testing."""
    return [
        JobListing(
            url="https://example.com/jobs/1",
            title="Python Developer",
            company="TechCo",
            description="Looking for a Python developer with 3+ years experience.",
            location="Remote",
        ),
        JobListing(
            url="https://example.com/jobs/2",
            title="Frontend Developer",
            company="WebCo",
            description="React and TypeScript expert needed.",
            location="New York",
        ),
    ]


@pytest.fixture
def sample_state(sample_resume: ResumeData, sample_jobs: list[JobListing]) -> ApplicationState:
    """Sample application state for testing."""
    return ApplicationState(
        resume_path="test_resume.pdf",
        job_urls=["https://example.com/jobs"],
        resume=sample_resume,
        jobs=sample_jobs,
        current_job_index=0,
    )
