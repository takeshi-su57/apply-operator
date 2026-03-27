"""Node: Fill and submit a job application form."""

import logging
from typing import Any

from apply_operator.state import ApplicationState
from apply_operator.tools.logging_utils import log_node

logger = logging.getLogger(__name__)


@log_node
def fill_application(state: ApplicationState) -> dict[str, Any]:
    """Use Playwright + LLM to fill out the job application form.

    Navigates to the application page, identifies form fields,
    uses LLM to determine appropriate values from resume data,
    fills the form, and submits.

    Currently a stub: marks the job as applied and advances the index.
    Real browser form filling will be implemented in issue 009.
    """
    idx = state.current_job_index
    jobs = list(state.jobs)
    job = jobs[idx].model_copy(update={"applied": True})
    jobs[idx] = job

    logger.info("Stub applied job: %s at %s", job.title, job.company)

    return {
        "jobs": jobs,
        "current_job_index": idx + 1,
        "total_applied": state.total_applied + 1,
    }
