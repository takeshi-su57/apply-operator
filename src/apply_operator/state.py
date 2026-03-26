"""LangGraph state definitions for the job application agent."""

from typing import Any

from pydantic import BaseModel, Field


class ResumeData(BaseModel):
    """Structured data extracted from a resume PDF."""

    raw_text: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class JobListing(BaseModel):
    """A single job listing found during search."""

    url: str
    title: str = ""
    company: str = ""
    description: str = ""
    location: str = ""
    fit_score: float = 0.0
    applied: bool = False
    error: str = ""


class ApplicationState(BaseModel):
    """Central state flowing through the LangGraph agent.

    Nodes receive this state and return a dict of fields to update.
    """

    # Inputs
    resume_path: str = ""
    job_urls: list[str] = Field(default_factory=list)

    # Parsed resume
    resume: ResumeData = Field(default_factory=ResumeData)

    # Job search results
    jobs: list[JobListing] = Field(default_factory=list)
    current_job_index: int = 0

    # Tracking
    total_applied: int = 0
    total_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
