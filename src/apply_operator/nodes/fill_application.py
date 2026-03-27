"""Node: Fill and submit a job application form."""

from typing import Any

from apply_operator.state import ApplicationState
from apply_operator.tools.logging_utils import log_node


@log_node
def fill_application(state: ApplicationState) -> dict[str, Any]:
    """Use Playwright + LLM to fill out the job application form.

    Navigates to the application page, identifies form fields,
    uses LLM to determine appropriate values from resume data,
    fills the form, and submits.
    """
    # TODO: Implement form filling via Playwright + LLM
    # For now, skip by advancing the index
    idx = state.current_job_index
    return {"current_job_index": idx + 1}
