"""Node: Search job sites for relevant listings."""

from typing import Any

from apply_operator.state import ApplicationState


def search_jobs(state: ApplicationState) -> dict[str, Any]:
    """Navigate to job site URLs and scrape job listings.

    Uses Playwright to browse each URL and extract job postings.
    """
    # TODO: Implement
    # 1. For each URL in state.job_urls:
    #    a. Open page with browser tool
    #    b. Extract job listings (title, company, description, apply URL)
    # 2. Return {"jobs": [JobListing(...)], "current_job_index": 0}
    return {}
