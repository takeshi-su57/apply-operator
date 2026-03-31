"""Shared test fixtures for apply-operator."""

import sqlite3
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import fitz  # PyMuPDF
import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from apply_operator.state import ApplicationState, JobListing, ResumeData


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a test PDF with sample resume text."""
    path = tmp_path / "resume.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "John Doe\njohn@example.com\nPython Developer")
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no text content."""
    path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


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
    return {
        "resume_path": "test_resume.pdf",
        "job_urls": ["https://example.com/jobs"],
        "resume": sample_resume,
        "jobs": sample_jobs,
        "current_job_index": 0,
        "total_applied": 0,
        "total_skipped": 0,
        "errors": [],
    }


@pytest.fixture
def checkpoint_saver() -> Iterator[SqliteSaver]:
    """In-memory sync SqliteSaver for read-only checkpoint operations."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    yield saver
    conn.close()


@pytest.fixture
async def async_checkpoint_saver() -> AsyncIterator[AsyncSqliteSaver]:
    """In-memory AsyncSqliteSaver for async graph execution tests."""
    async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        await saver.setup()
        yield saver
