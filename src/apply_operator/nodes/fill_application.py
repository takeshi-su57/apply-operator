"""Node: Fill and submit a job application form."""

import json
import logging
import re
from typing import Any

from playwright.async_api import Page

from apply_operator.config import get_settings
from apply_operator.prompts.form_filling import DETECT_FORM_PAGE_TYPE, MAP_FORM_FIELDS
from apply_operator.state import ApplicationState, JobListing, ResumeData
from apply_operator.tools.browser import (
    FormField,
    get_form_fields,
    get_page_text,
    get_page_with_session,
    handle_captcha_if_present,
    take_screenshot,
    wait_for_page_ready,
)
from apply_operator.tools.llm_provider import call_llm
from apply_operator.tools.logging_utils import log_node

logger = logging.getLogger(__name__)

_SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:text("Submit")',
    'button:text("Apply")',
    'button:text("Send")',
    'button:text("Submit Application")',
]

_NEXT_PAGE_SELECTORS = [
    'button:text("Next")',
    'button:text("Continue")',
    'a:text("Next")',
    'button:text("next")',
    'button:text("continue")',
]

_MAX_FORM_PAGES = 10


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _format_experience(experience: list[dict[str, Any]]) -> str:
    """Format experience list into a readable string for the prompt."""
    if not experience:
        return "No experience listed"
    parts = []
    for exp in experience:
        title = exp.get("title", "Unknown")
        company = exp.get("company", "Unknown")
        duration = exp.get("duration", "")
        desc = exp.get("description", "")
        entry = f"{title} at {company}"
        if duration:
            entry += f" ({duration})"
        if desc:
            entry += f" — {desc}"
        parts.append(entry)
    return "; ".join(parts)


def _format_education(education: list[dict[str, Any]]) -> str:
    """Format education list into a readable string for the prompt."""
    if not education:
        return "No education listed"
    parts = []
    for edu in education:
        degree = edu.get("degree", "Unknown")
        institution = edu.get("institution", "Unknown")
        year = edu.get("year", "")
        entry = f"{degree} from {institution}"
        if year:
            entry += f" ({year})"
        parts.append(entry)
    return "; ".join(parts)


def _format_fields_for_prompt(fields: list[FormField]) -> str:
    """Format form fields into a readable list for the LLM prompt."""
    lines = []
    for f in fields:
        line = f'- name={f["name"]}, label="{f["label"]}", type={f["field_type"]}'
        if f["required"]:
            line += ", required"
        if f["options"]:
            opts = ", ".join(o["text"] for o in f["options"])
            line += f", options=[{opts}]"
        lines.append(line)
    return "\n".join(lines)


def _map_fields_with_llm(
    fields: list[FormField], resume: ResumeData, job: JobListing
) -> dict[str, str]:
    """Use LLM to map resume data to form field values.

    Args:
        fields: Extracted form fields from the page.
        resume: Parsed resume data.
        job: Current job listing being applied to.

    Returns:
        Mapping of field name to value to fill in.
    """
    prompt = MAP_FORM_FIELDS.format(
        job_title=job.title or "Unknown Position",
        company=job.company or "Unknown Company",
        form_fields=_format_fields_for_prompt(fields),
        name=resume.name,
        email=resume.email,
        phone=resume.phone,
        summary=resume.summary or "No summary available",
        skills=", ".join(resume.skills) if resume.skills else "None listed",
        experience=_format_experience(resume.experience),
        education=_format_education(resume.education),
    )

    try:
        response = call_llm(prompt, purpose=f"map_form_fields for {job.title} at {job.company}")
        cleaned = _strip_markdown_json(response)
        mapping = json.loads(cleaned)
        if not isinstance(mapping, dict):
            logger.warning("LLM returned non-dict for field mapping: %s", type(mapping))
            return {}
        return {str(k): str(v) for k, v in mapping.items()}
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse LLM field mapping: %s", e)
        return {}


async def _fill_field(page: Page, field: FormField, value: str, resume_path: str) -> None:
    """Fill a single form field with the given value.

    Args:
        page: Playwright page.
        field: Form field metadata.
        value: Value to fill in.
        resume_path: Path to resume PDF for file upload fields.
    """
    selector = field["selector"]
    field_type = field["field_type"]

    try:
        if field_type == "file":
            if value == "RESUME_FILE" and resume_path:
                file_input = await page.query_selector(selector)
                if file_input:
                    await file_input.set_input_files(resume_path)
                    logger.debug("Uploaded resume to %s", field["name"])
            return

        if field_type == "select":
            await page.select_option(selector, label=value)
            logger.debug("Selected '%s' for %s", value, field["name"])
            return

        if field_type in ("checkbox", "radio"):
            if value.lower() in ("true", "yes", "on", "1"):
                await page.check(selector)
            else:
                await page.uncheck(selector)
            logger.debug("Set %s to %s for %s", field_type, value, field["name"])
            return

        # text, email, tel, url, textarea
        await page.fill(selector, value)
        logger.debug("Filled %s with %d chars", field["name"], len(value))
    except Exception as e:
        logger.warning("Failed to fill field %s: %s", field["name"], e)


async def _find_and_click(page: Page, selectors: list[str]) -> bool:
    """Try to find and click the first visible element matching any selector.

    Args:
        page: Playwright page.
        selectors: CSS/text selectors to try in order.

    Returns:
        True if an element was found and clicked.
    """
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                await element.click()
                await page.wait_for_load_state("domcontentloaded")
                return True
        except Exception:
            continue
    return False


async def _verify_submission(page: Page) -> bool:
    """Check if the current page indicates a successful form submission.

    Uses LLM to classify the page, with a text-based heuristic fallback.

    Args:
        page: Playwright page after form submission.

    Returns:
        True if the page appears to be a confirmation page.
    """
    text = await get_page_text(page)
    if not text.strip():
        return False

    # Heuristic fallback keywords
    confirmation_keywords = [
        "thank you",
        "application received",
        "successfully submitted",
        "application submitted",
        "we have received",
        "confirmation",
    ]
    text_lower = text.lower()[:2000]
    if any(kw in text_lower for kw in confirmation_keywords):
        logger.info("Submission confirmed via text heuristic")
        return True

    # LLM classification
    try:
        prompt = DETECT_FORM_PAGE_TYPE.format(page_text=text[:2000])
        response = call_llm(prompt, purpose="verify_submission page type")
        cleaned = _strip_markdown_json(response)
        data = json.loads(cleaned)
        page_type = str(data.get("page_type", "other"))
        logger.info("LLM classified post-submit page as: %s", page_type)
        return page_type == "confirmation"
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse submission verification: %s", e)
        return False


@log_node
async def fill_application(state: ApplicationState) -> dict[str, Any]:
    """Use Playwright + LLM to fill out the job application form.

    Navigates to the application page, identifies form fields,
    uses LLM to determine appropriate values from resume data,
    fills the form, handles CAPTCHAs, and submits.
    """
    idx = state.current_job_index
    jobs = list(state.jobs)
    job = jobs[idx]
    errors = list(state.errors)

    try:
        async with get_page_with_session(job.url) as page:
            settings = get_settings()
            logger.info("Navigating to application page: %s", job.url)
            await page.goto(job.url, timeout=settings.browser_timeout)
            await wait_for_page_ready(page)

            # Pre-form CAPTCHA check
            await handle_captcha_if_present(page)

            form_filled = False

            for page_num in range(_MAX_FORM_PAGES):
                fields = await get_form_fields(page)
                if not fields:
                    logger.info("No form fields found on page %d", page_num + 1)
                    break

                logger.info("Page %d: found %d form fields", page_num + 1, len(fields))

                # LLM maps resume data to form fields
                mapping = _map_fields_with_llm(fields, state.resume, job)
                if not mapping:
                    logger.warning("LLM returned empty field mapping on page %d", page_num + 1)

                # Fill each mapped field
                filled_count = 0
                for field in fields:
                    value = mapping.get(field["name"], "")
                    if not value:
                        continue
                    await _fill_field(page, field, value, state.resume_path)
                    filled_count += 1

                logger.info(
                    "Filled %d/%d fields on page %d",
                    filled_count,
                    len(fields),
                    page_num + 1,
                )
                form_filled = True

                # Pre-submit CAPTCHA check
                await handle_captcha_if_present(page)

                # Try next-page button first
                if await _find_and_click(page, _NEXT_PAGE_SELECTORS):
                    logger.info("Clicked next page button, advancing to page %d", page_num + 2)
                    await wait_for_page_ready(page)
                    continue

                # Try submit button
                if await _find_and_click(page, _SUBMIT_SELECTORS):
                    logger.info("Clicked submit button")
                    break

                # Neither found — dead end
                logger.warning("No next/submit button found on page %d", page_num + 1)
                break

            await wait_for_page_ready(page)

            # Verify submission
            success = form_filled and await _verify_submission(page)

            # Take evidence screenshot
            try:
                await take_screenshot(page, f"application_{job.company}_{idx}")
            except Exception:
                logger.debug("Failed to take screenshot", exc_info=True)

        if success:
            logger.info("Successfully applied to %s at %s", job.title, job.company)
            jobs[idx] = job.model_copy(update={"applied": True})
            return {
                "jobs": jobs,
                "current_job_index": idx + 1,
                "total_applied": state.total_applied + 1,
            }
        else:
            msg = f"Submission not confirmed for {job.title} at {job.company}"
            logger.warning(msg)
            jobs[idx] = job.model_copy(update={"error": msg})
            errors.append(msg)
            return {
                "jobs": jobs,
                "current_job_index": idx + 1,
                "total_skipped": state.total_skipped + 1,
                "errors": errors,
            }

    except Exception as e:
        msg = f"Failed to apply to {job.title} at {job.company}: {e}"
        logger.error(msg)
        jobs[idx] = job.model_copy(update={"error": str(e)})
        errors.append(msg)
        return {
            "jobs": jobs,
            "current_job_index": idx + 1,
            "errors": errors,
        }
