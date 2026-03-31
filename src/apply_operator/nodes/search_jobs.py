"""Node: Search job sites for relevant listings."""

import json
import logging
import re
from typing import Any

from playwright.async_api import Page

from apply_operator.prompts.job_matching import EXTRACT_JOBS
from apply_operator.state import ApplicationState, JobListing
from apply_operator.tools.browser import (
    get_page_text,
    get_page_with_session,
    navigate_with_retry,
    wait_for_page_ready,
    wait_for_user,
)
from apply_operator.tools.llm_provider import call_llm
from apply_operator.tools.logging_utils import log_node
from apply_operator.tools.retry import CaptchaBlockError, FatalConfigError, PageTimeoutError

logger = logging.getLogger(__name__)

_LOGIN_INDICATORS = ["sign in", "log in", "login", "signin"]

_NEXT_PAGE_SELECTORS = [
    'a[aria-label="Next"]',
    'a:text("Next")',
    'button:text("Load more")',
    'button:text("Show more")',
    '[class*="next"]',
    '[class*="pagination"] a:last-child',
]


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


async def _detect_login_required(page: Page) -> bool:
    """Check if the current page is a login wall."""
    url_lower = page.url.lower()
    if any(indicator in url_lower for indicator in _LOGIN_INDICATORS):
        return True

    text = await get_page_text(page)
    text_start = text.lower()[:500]
    return any(indicator in text_start for indicator in _LOGIN_INDICATORS)


async def _extract_jobs_from_page(page: Page, url: str) -> list[JobListing]:
    """Use LLM to extract job listings from the current page."""
    text = await get_page_text(page)
    if not text.strip():
        return []

    prompt = EXTRACT_JOBS.format(page_text=text[:8000], url=url)
    response = call_llm(prompt, purpose=f"extract_jobs from {url}")
    cleaned = _strip_markdown_json(response)

    try:
        listings = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse job extraction JSON for %s", url)
        return []

    if not isinstance(listings, list):
        logger.warning("LLM returned non-list for job extraction at %s", url)
        return []

    jobs: list[JobListing] = []
    for item in listings:
        if not isinstance(item, dict):
            continue
        jobs.append(
            JobListing(
                url=item.get("apply_url") or url,
                title=item.get("title", ""),
                company=item.get("company", ""),
                description=item.get("description", ""),
                location=item.get("location", ""),
            )
        )
    return jobs


async def _find_next_page(page: Page) -> bool:
    """Click next page / load more if available. Returns True if navigated."""
    for selector in _NEXT_PAGE_SELECTORS:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                await element.click()
                await page.wait_for_load_state("domcontentloaded")
                await wait_for_page_ready(page)
                return True
        except Exception:
            continue
    return False


@log_node
async def search_jobs(state: ApplicationState) -> dict[str, Any]:
    """Navigate to job site URLs and scrape job listings.

    Uses Playwright to browse each URL and extract job postings.
    Handles login walls via user intervention and follows pagination.
    """
    all_jobs: list[JobListing] = []
    errors = list(state.errors)

    for url in state.job_urls:
        try:
            logger.info("Opening browser for %s", url)
            async with get_page_with_session(url) as page:
                logger.info("Navigating to %s", url)
                await navigate_with_retry(page, url)

                await wait_for_page_ready(page)
                logger.info("Page loaded, checking for login wall")
                if await _detect_login_required(page):
                    await wait_for_user(page, f"Login required at {url}. Please log in.")
                    await wait_for_page_ready(page)

                logger.info("Extracting jobs from %s", url)
                while True:
                    page_jobs = await _extract_jobs_from_page(page, url)
                    all_jobs.extend(page_jobs)
                    if not await _find_next_page(page):
                        break

            logger.info("Found %d jobs from %s", len(all_jobs), url)
        except FatalConfigError:
            raise
        except (PageTimeoutError, CaptchaBlockError) as e:
            errors.append(f"Failed to search {url}: {e}")
            logger.warning("Skipping %s: %s", url, e)
        except Exception as e:
            errors.append(f"Failed to search {url}: {e}")
            logger.error("Error searching %s: %s", url, e)

    return {"jobs": all_jobs, "current_job_index": 0, "errors": errors}
