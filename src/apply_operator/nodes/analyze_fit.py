"""Node: Analyze fit between resume and current job listing."""

from apply_operator.state import ApplicationState


def analyze_fit(state: ApplicationState) -> dict:
    """Use LLM to score how well the resume matches the current job.

    Returns a fit score (0.0 to 1.0) for the current job listing.
    """
    # TODO: Implement
    # 1. Get current job: state.jobs[state.current_job_index]
    # 2. Build prompt with resume data + job description
    # 3. Call LLM for fit analysis
    # 4. Parse score from response
    # 5. Update job's fit_score
    # 6. Return updated state fields
    return {}
