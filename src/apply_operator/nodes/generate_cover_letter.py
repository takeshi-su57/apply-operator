"""Node: Generate a tailored cover letter for the current job."""

import json
import logging
import re
from typing import Any

from apply_operator.prompts.cover_letter import GENERATE_COVER_LETTER
from apply_operator.state import ApplicationState
from apply_operator.tools.llm_provider import call_llm
from apply_operator.tools.logging_utils import log_node
from apply_operator.tools.retry import FatalConfigError

logger = logging.getLogger(__name__)


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _format_experience(experience: list[dict[str, Any]]) -> str:
    """Format experience list into a readable string for the prompt."""
    if not experience:
        return "No experience listed"
    parts = []
    for exp in experience:
        title = exp.get("title", "Unknown")
        company = exp.get("company", "Unknown")
        duration = exp.get("duration", "")
        desc = exp.get("description", "")
        entry = f"{title} at {company}"
        if duration:
            entry += f" ({duration})"
        if desc:
            entry += f" — {desc}"
        parts.append(entry)
    return "; ".join(parts)


@log_node
def generate_cover_letter(state: ApplicationState) -> dict[str, Any]:
    """Generate a tailored cover letter for the current high-fit job.

    Uses LLM to create a professional cover letter based on the candidate's
    resume and the job description. Stores the result on the JobListing.
    """
    idx = state["current_job_index"]
    if idx >= len(state["jobs"]):
        return {}

    job = state["jobs"][idx]
    resume = state["resume"]

    prompt = GENERATE_COVER_LETTER.format(
        name=resume.name,
        summary=resume.summary or "No summary available",
        skills=", ".join(resume.skills) if resume.skills else "None listed",
        experience=_format_experience(resume.experience),
        job_title=job.title,
        company=job.company,
        job_description=job.description,
    )

    cover_letter = ""
    errors: list[str] = []

    try:
        response = call_llm(
            prompt,
            purpose=f"generate_cover_letter for {job.title} at {job.company}",
            expect_json=True,
        )
        cleaned = _strip_markdown_json(response)
        data = json.loads(cleaned)
        cover_letter = str(data.get("cover_letter", ""))
    except FatalConfigError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
        logger.error("Failed to generate cover letter for %s: %s", job.url, e)
        errors.append(f"Cover letter generation failed for {job.url}: {e}")

    logger.info(
        "Cover letter for %s (%s): %d chars",
        job.title,
        job.company,
        len(cover_letter),
    )

    updated_jobs = list(state["jobs"])
    updated_jobs[idx] = job.model_copy(update={"cover_letter": cover_letter})

    result: dict[str, Any] = {"jobs": updated_jobs}
    if errors:
        result["errors"] = errors
    return result
