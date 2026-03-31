"""LangGraph state definitions for the job application agent."""

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field, model_validator


class ResumeData(BaseModel):
    """Structured data extracted from a resume PDF.

    All fields except raw_text are optional — the LLM may return null
    for missing sections. A pre-validator coerces None to the field default
    so downstream code can always assume non-None values.
    """

    raw_text: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""

    @model_validator(mode="before")
    @classmethod
    def coerce_none_to_defaults(cls, values: Any) -> Any:
        """Replace None values with field defaults so Pydantic doesn't reject them."""
        if not isinstance(values, dict):
            return values
        defaults: dict[str, Any] = {
            "name": "",
            "email": "",
            "phone": "",
            "skills": [],
            "experience": [],
            "education": [],
            "summary": "",
        }
        for field, default in defaults.items():
            if values.get(field) is None:
                values[field] = default
        return values


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


class ApplicationState(TypedDict, total=False):
    """Central state flowing through the LangGraph agent.

    Nodes receive this state as a dict and return a dict of fields to update.
    The ``errors`` field uses an ``operator.add`` reducer so that each node
    can return only its *new* errors and LangGraph concatenates them
    automatically.
    """

    # Inputs
    resume_path: str
    job_urls: list[str]

    # Parsed resume
    resume: ResumeData

    # Job search results
    jobs: list[JobListing]
    current_job_index: int

    # Tracking
    total_applied: int
    total_skipped: int
    errors: Annotated[list[str], operator.add]
