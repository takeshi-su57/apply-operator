"""Indeed job site adapter for job search and multi-step applications."""

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

# Indeed-specific selectors
_JOB_CARD_SELECTORS = [
    ".job_seen_beacon",
    ".jobsearch-ResultsList .result",
    '[data-testid="job-card"]',
    ".tapItem",
]

_APPLY_BUTTON_SELECTORS = [
    "#indeedApplyButton",
    'button[id*="indeedApply"]',
    'button:has-text("Apply now")',
    'a:has-text("Apply now")',
]

_NEXT_PAGE_SELECTORS = [
    'a[data-testid="pagination-page-next"]',
    'a[aria-label="Next Page"]',
    'nav[aria-label="pagination"] a:last-child',
]

_CONTINUE_SELECTORS = [
    'button:has-text("Continue")',
    'button[data-testid="continue-button"]',
    'button:has-text("Next")',
]

_SUBMIT_SELECTORS = [
    'button:has-text("Submit your application")',
    'button:has-text("Submit")',
    'button[data-testid="submit-button"]',
]


class IndeedAdapter(JobSiteAdapter):
    """Adapter for Indeed job search and application."""

    domain = "indeed.com"

    async def search_jobs(self, page: Page, url: str) -> list[JobListing]:
        """Extract job listings from Indeed search results."""
        jobs: list[JobListing] = []

        for selector in _JOB_CARD_SELECTORS:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Found %d job cards via %s", len(cards), selector)
                break
        else:
            logger.warning("No job cards found on Indeed page")
            return jobs

        for card in cards:
            try:
                title_el = await card.query_selector(
                    "h2.jobTitle a, .jobTitle span, [data-testid='job-title']"
                )
                company_el = await card.query_selector(
                    "[data-testid='company-name'], .companyName, .company"
                )
                location_el = await card.query_selector(
                    "[data-testid='text-location'], .companyLocation, .location"
                )
                link_el = await card.query_selector("h2.jobTitle a, a[data-jk], a.jcs-JobTitle")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                location = (await location_el.inner_text()).strip() if location_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                job_url = href if href and href.startswith("http") else f"https://indeed.com{href}"

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
                logger.debug("Failed to extract Indeed job card: %s", e)
                continue

        logger.info("Extracted %d jobs from Indeed", len(jobs))
        return jobs

    async def fill_application(self, page: Page, resume: ResumeData, job: JobListing) -> bool:
        """Handle Indeed's multi-step application flow."""
        # Click Apply button
        apply_clicked = False
        for selector in _APPLY_BUTTON_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    apply_clicked = True
                    logger.info("Clicked Indeed Apply button via %s", selector)
                    break
            except Exception:
                continue

        if not apply_clicked:
            logger.warning("Indeed Apply button not found — falling back to generic")
            return False

        await page.wait_for_timeout(1000)

        # Step through multi-page application
        max_steps = 10
        for step in range(max_steps):
            await wait_for_page_ready(page)

            fields = await get_form_fields(page)
            if fields:
                logger.info("Indeed step %d: %d fields", step + 1, len(fields))
                for field in fields:
                    value = self._resolve_field_value(field, resume)
                    if value:
                        try:
                            el = await page.query_selector(field["selector"])
                            if el:
                                await el.fill(value)
                        except Exception as e:
                            logger.debug("Failed to fill field %s: %s", field["name"], e)

            # Try submit first, then continue
            submitted = await self._click_first_visible(page, _SUBMIT_SELECTORS)
            if submitted:
                logger.info("Submitted Indeed application")
                await page.wait_for_timeout(2000)
                return True

            advanced = await self._click_first_visible(page, _CONTINUE_SELECTORS)
            if not advanced:
                logger.warning("No continue/submit button at step %d", step + 1)
                break

            await page.wait_for_timeout(500)

        logger.warning("Indeed application flow did not reach submission")
        return False

    async def find_next_page(self, page: Page) -> bool:
        """Navigate to the next page of Indeed search results."""
        return await self._click_first_visible(page, _NEXT_PAGE_SELECTORS)

    def _resolve_field_value(self, field: FormField, resume: ResumeData) -> str:
        """Map a form field to a resume value based on label/name heuristics."""
        label = (field.get("label", "") + " " + field.get("name", "")).lower()
        field_type = field.get("field_type", "")

        if field_type == "file":
            return ""
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
