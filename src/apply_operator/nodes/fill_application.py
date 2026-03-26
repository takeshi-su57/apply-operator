"""Node: Fill and submit a job application form."""

from apply_operator.state import ApplicationState


def fill_application(state: ApplicationState) -> dict:
    """Use Playwright + LLM to fill out the job application form.

    Navigates to the application page, identifies form fields,
    uses LLM to determine appropriate values from resume data,
    fills the form, and submits.
    """
    # TODO: Implement
    # 1. Get current job: state.jobs[state.current_job_index]
    # 2. Navigate to job application URL with browser tool
    # 3. Identify form fields on the page
    # 4. Use LLM to map resume data to form fields
    # 5. Fill form fields with Playwright
    # 6. Submit application
    # 7. Update job.applied = True, increment total_applied
    # 8. Advance current_job_index
    # 9. Return updated state fields
    return {}
