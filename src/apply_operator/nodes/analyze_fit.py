"""Node: Analyze fit between resume and current job listing."""

import json
import logging
import re
from typing import Any

from apply_operator.prompts.job_matching import ANALYZE_FIT
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
def analyze_fit(state: ApplicationState) -> dict[str, Any]:
    """Use LLM to score how well the resume matches the current job.

    Scores the job at current_job_index without advancing the index.
    The graph's conditional edges handle routing (apply/skip/report).
    """
    idx = state["current_job_index"]
    if idx >= len(state["jobs"]):
        return {}

    job = state["jobs"][idx]

    resume = state["resume"]
    prompt = ANALYZE_FIT.format(
        name=resume.name,
        skills=", ".join(resume.skills) if resume.skills else "None listed",
        experience=_format_experience(resume.experience),
        job_title=job.title,
        company=job.company,
        job_description=job.description,
    )

    score = 0.0
    reasoning = ""
    errors: list[str] = []

    try:
        response = call_llm(
            prompt,
            purpose=f"analyze_fit for {job.title} at {job.company}",
            expect_json=True,
        )
        cleaned = _strip_markdown_json(response)
        data = json.loads(cleaned)

        raw_score = float(data.get("score", 0.0))
        score = max(0.0, min(1.0, raw_score))
        reasoning = str(data.get("reasoning", ""))

        if raw_score != score:
            logger.warning(
                "Fit score %.2f clamped to %.2f for %s",
                raw_score,
                score,
                job.url,
            )
    except FatalConfigError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
        logger.error("Failed to parse LLM fit response for %s: %s", job.url, e)
        errors.append(f"Fit analysis failed for {job.url}: {e}")

    logger.info(
        "Fit score for %s (%s): %.2f — %s",
        job.title,
        job.company,
        score,
        reasoning or "no reasoning",
    )

    updated_jobs = list(state["jobs"])
    updated_jobs[idx] = job.model_copy(update={"fit_score": score})

    result: dict[str, Any] = {"jobs": updated_jobs}
    if errors:
        result["errors"] = errors
    return result
