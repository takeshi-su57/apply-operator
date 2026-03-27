"""Node: Analyze fit between resume and current job listing."""

from typing import Any

from apply_operator.state import ApplicationState


def analyze_fit(state: ApplicationState) -> dict[str, Any]:
    """Use LLM to score how well the resume matches the current job.

    Returns a fit score (0.0 to 1.0) for the current job listing.
    """
    # TODO: Implement LLM-based fit scoring
    # For now, skip all jobs by advancing the index
    idx = state.current_job_index
    if idx >= len(state.jobs):
        return {}
    jobs = list(state.jobs)
    jobs[idx] = jobs[idx].model_copy(update={"fit_score": 0.0})
    return {
        "jobs": jobs,
        "current_job_index": idx + 1,
        "total_skipped": state.total_skipped + 1,
    }
