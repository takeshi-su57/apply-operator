"""LinkedIn job site adapter for Easy Apply and job search."""

import logging

from playwright.async_api import Page

from apply_operator.state import JobListing, ResumeData
from apply_operator.tools.adapters.base import JobSiteAdapter
from apply_operator.tools.browser import (
    FormField,
    get_form_fields,
    wait_for_page_ready,
)

logger = logging.getLogger(__name__)

# LinkedIn-specific selectors
_JOB_CARD_SELECTORS = [
    ".job-card-container",
    ".jobs-search-results__list-item",
    "[data-job-id]",
]

_EASY_APPLY_BUTTON = [
    "button.jobs-apply-button",
    'button[aria-label*="Easy Apply"]',
    ".jobs-apply-button--top-card",
]

_NEXT_PAGE_SELECTORS = [
    'button[aria-label="Next"]',
    "li.artdeco-pagination__indicator--number + li button",
]

_MODAL_NEXT_SELECTORS = [
    'button[aria-label="Continue to next step"]',
    'button[aria-label="Review your application"]',
    'button span:text("Next")',
]

_MODAL_SUBMIT_SELECTORS = [
    'button[aria-label="Submit application"]',
    'button span:text("Submit application")',
]


class LinkedInAdapter(JobSiteAdapter):
    """Adapter for LinkedIn job search and Easy Apply."""

    domain = "linkedin.com"

    async def search_jobs(self, page: Page, url: str) -> list[JobListing]:
        """Extract job listings from LinkedIn search results."""
        jobs: list[JobListing] = []

        for selector in _JOB_CARD_SELECTORS:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Found %d job cards via %s", len(cards), selector)
                break
        else:
            logger.warning("No job cards found on LinkedIn page")
            return jobs

        for card in cards:
            try:
                title_el = await card.query_selector(
                    ".job-card-list__title, .artdeco-entity-lockup__title"
                )
                company_el = await card.query_selector(
                    ".artdeco-entity-lockup__subtitle, .job-card-container__company-name"
                )
                location_el = await card.query_selector(
                    ".artdeco-entity-lockup__caption, .job-card-container__metadata-wrapper"
                )
                link_el = await card.query_selector("a[href*='/jobs/view/']")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                location = (await location_el.inner_text()).strip() if location_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                job_url = (
                    href if href and href.startswith("http") else f"https://linkedin.com{href}"
                )

                if title or company:
                    jobs.append(
                        JobListing(
                            url=job_url,
                            title=title,
                            company=company,
                            location=location,
                        )
                    )
            except Exception as e:
                logger.debug("Failed to extract LinkedIn job card: %s", e)
                continue

        logger.info("Extracted %d jobs from LinkedIn", len(jobs))
        return jobs

    async def fill_application(self, page: Page, resume: ResumeData, job: JobListing) -> bool:
        """Handle LinkedIn Easy Apply flow."""
        # Click Easy Apply button
        easy_apply_clicked = False
        for selector in _EASY_APPLY_BUTTON:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    easy_apply_clicked = True
                    logger.info("Clicked Easy Apply button via %s", selector)
                    break
            except Exception:
                continue

        if not easy_apply_clicked:
            logger.warning("Easy Apply button not found — falling back to generic")
            return False

        await page.wait_for_timeout(1000)

        # Step through Easy Apply modal pages
        max_steps = 10
        for step in range(max_steps):
            await wait_for_page_ready(page)

            # Check for form fields in modal
            fields = await get_form_fields(page)
            if fields:
                logger.info("Easy Apply step %d: %d fields", step + 1, len(fields))
                # Fill fields using page text context for LLM
                for field in fields:
                    value = self._resolve_field_value(field, resume)
                    if value:
                        try:
                            el = await page.query_selector(field["selector"])
                            if el:
                                await el.fill(value)
                        except Exception as e:
                            logger.debug("Failed to fill field %s: %s", field["name"], e)

            # Try submit first, then next
            submitted = await self._click_first_visible(page, _MODAL_SUBMIT_SELECTORS)
            if submitted:
                logger.info("Submitted LinkedIn Easy Apply")
                await page.wait_for_timeout(2000)
                return True

            advanced = await self._click_first_visible(page, _MODAL_NEXT_SELECTORS)
            if not advanced:
                logger.warning("No next/submit button found at step %d", step + 1)
                break

            await page.wait_for_timeout(500)

        logger.warning("Easy Apply flow did not reach submission")
        return False

    async def find_next_page(self, page: Page) -> bool:
        """Navigate to the next page of LinkedIn search results."""
        return await self._click_first_visible(page, _NEXT_PAGE_SELECTORS)

    def _resolve_field_value(self, field: FormField, resume: ResumeData) -> str:
        """Map a form field to a resume value based on label/name heuristics."""
        label = (field.get("label", "") + " " + field.get("name", "")).lower()
        field_type = field.get("field_type", "")

        if field_type == "file":
            return ""  # File uploads handled separately
        if "email" in label:
            return resume.email
        if "phone" in label or "mobile" in label:
            return resume.phone
        if "name" in label and "first" in label:
            return resume.name.split()[0] if resume.name else ""
        if "name" in label and "last" in label:
            parts = resume.name.split()
            return parts[-1] if len(parts) > 1 else ""
        if "name" in label:
            return resume.name
        return ""

    @staticmethod
    async def _click_first_visible(page: Page, selectors: list[str]) -> bool:
        """Click the first visible element matching any selector."""
        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                continue
        return False
