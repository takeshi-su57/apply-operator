"""Base class for job site adapters."""

import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from playwright.async_api import Page

from apply_operator.state import JobListing, ResumeData

logger = logging.getLogger(__name__)


class JobSiteAdapter(ABC):
    """Base class for site-specific job site adapters.

    Adapters handle site-specific quirks: custom UI components, multi-step
    application flows, and non-standard page structures. They do NOT manage
    authentication — that is handled by the shared session system.
    """

    domain: str

    def matches(self, url: str) -> bool:
        """Check if this adapter handles the given URL."""
        parsed = urlparse(url)
        return self.domain in parsed.netloc

    @abstractmethod
    async def search_jobs(self, page: Page, url: str) -> list[JobListing]:
        """Extract job listings from a site-specific page.

        Args:
            page: Playwright page (already navigated and ready).
            url: The source URL being searched.

        Returns:
            List of extracted job listings.
        """

    @abstractmethod
    async def fill_application(self, page: Page, resume: ResumeData, job: JobListing) -> bool:
        """Fill and submit a job application using site-specific flow.

        Args:
            page: Playwright page (already navigated to the job URL).
            resume: Parsed resume data.
            job: The job listing being applied to.

        Returns:
            True if the application was submitted successfully.
        """

    @abstractmethod
    async def find_next_page(self, page: Page) -> bool:
        """Navigate to the next page of search results.

        Args:
            page: Playwright page on the current results page.

        Returns:
            True if navigation to the next page succeeded.
        """
