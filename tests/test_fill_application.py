"""Tests for the fill_application node."""

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from apply_operator.nodes.fill_application import (
    _fill_field,
    _find_and_click,
    _map_fields_with_llm,
    _strip_markdown_json,
    _verify_submission,
    fill_application,
)
from apply_operator.state import ApplicationState, JobListing, ResumeData
from apply_operator.tools.browser import FormField


def _make_state(**kwargs: Any) -> ApplicationState:
    """Create an ApplicationState with sensible defaults for fill_application tests."""
    defaults: dict[str, Any] = {
        "resume_path": "/tmp/resume.pdf",
        "job_urls": ["https://example.com/jobs"],
        "resume": ResumeData(
            raw_text="John Doe\njohn@example.com\nSoftware Engineer",
            name="John Doe",
            email="john@example.com",
            phone="555-0100",
            skills=["Python", "TypeScript"],
            experience=[
                {
                    "title": "Senior Engineer",
                    "company": "Acme Corp",
                    "duration": "2020-2024",
                    "description": "Led backend development",
                }
            ],
            education=[{"degree": "BS Computer Science", "institution": "MIT", "year": "2020"}],
            summary="Experienced software engineer.",
        ),
        "jobs": [
            JobListing(
                url="https://example.com/apply/1",
                title="Python Developer",
                company="TechCo",
                description="Looking for a Python developer.",
                fit_score=0.8,
            ),
        ],
        "current_job_index": 0,
    }
    defaults.update(kwargs)
    return ApplicationState(**defaults)


def _mock_page(url: str = "https://example.com/apply/1") -> AsyncMock:
    """Create a mock Playwright page with standard methods."""
    page = AsyncMock()
    page.url = url
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.select_option = AsyncMock()
    page.check = AsyncMock()
    page.uncheck = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock(return_value=[])
    page.screenshot = AsyncMock()
    return page


@asynccontextmanager
async def _fake_session(page: AsyncMock):  # type: ignore[no-untyped-def]
    """Fake get_page_with_session context manager."""
    yield page


def _text_field(name: str = "full_name", label: str = "Full Name") -> FormField:
    """Create a sample text FormField."""
    return FormField(
        tag="input",
        field_type="text",
        name=name,
        label=label,
        required=True,
        selector=f'[name="{name}"]',
        options=[],
    )


def _select_field(
    name: str = "country",
    label: str = "Country",
    options: list[dict[str, str]] | None = None,
) -> FormField:
    """Create a sample select FormField."""
    if options is None:
        options = [
            {"value": "us", "text": "United States"},
            {"value": "uk", "text": "United Kingdom"},
        ]
    return FormField(
        tag="select",
        field_type="select",
        name=name,
        label=label,
        required=False,
        selector=f'[name="{name}"]',
        options=options,
    )


def _file_field(name: str = "resume") -> FormField:
    """Create a sample file upload FormField."""
    return FormField(
        tag="input",
        field_type="file",
        name=name,
        label="Upload Resume",
        required=False,
        selector=f'[name="{name}"]',
        options=[],
    )


def _checkbox_field(name: str = "agree_terms") -> FormField:
    """Create a sample checkbox FormField."""
    return FormField(
        tag="input",
        field_type="checkbox",
        name=name,
        label="I agree to the terms",
        required=True,
        selector=f'[name="{name}"]',
        options=[],
    )


# ---------------------------------------------------------------------------
# Unit tests: _strip_markdown_json
# ---------------------------------------------------------------------------


class TestStripMarkdownJson:
    def test_strips_code_fences(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _strip_markdown_json(text) == '{"key": "value"}'

    def test_returns_plain_json(self) -> None:
        text = '{"key": "value"}'
        assert _strip_markdown_json(text) == '{"key": "value"}'


# ---------------------------------------------------------------------------
# Unit tests: _map_fields_with_llm
# ---------------------------------------------------------------------------


class TestMapFieldsWithLlm:
    def test_parses_valid_json_mapping(self) -> None:
        fields = [_text_field("name", "Full Name"), _text_field("email", "Email")]
        resume = ResumeData(name="John Doe", email="john@example.com")
        job = JobListing(url="https://example.com/apply", title="Dev", company="Co")

        llm_response = json.dumps({"name": "John Doe", "email": "john@example.com"})
        with patch(
            "apply_operator.nodes.fill_application.call_llm",
            return_value=llm_response,
        ):
            result = _map_fields_with_llm(fields, resume, job)

        assert result == {"name": "John Doe", "email": "john@example.com"}

    def test_handles_markdown_wrapped_json(self) -> None:
        fields = [_text_field()]
        resume = ResumeData(name="John")
        job = JobListing(url="https://example.com/apply", title="Dev", company="Co")

        wrapped = '```json\n{"full_name": "John"}\n```'
        with patch(
            "apply_operator.nodes.fill_application.call_llm",
            return_value=wrapped,
        ):
            result = _map_fields_with_llm(fields, resume, job)

        assert result == {"full_name": "John"}

    def test_returns_empty_on_invalid_json(self) -> None:
        fields = [_text_field()]
        resume = ResumeData(name="John")
        job = JobListing(url="https://example.com/apply", title="Dev", company="Co")

        with patch(
            "apply_operator.nodes.fill_application.call_llm",
            return_value="not valid json {{{",
        ):
            result = _map_fields_with_llm(fields, resume, job)

        assert result == {}

    def test_returns_empty_on_non_dict_response(self) -> None:
        fields = [_text_field()]
        resume = ResumeData(name="John")
        job = JobListing(url="https://example.com/apply", title="Dev", company="Co")

        with patch(
            "apply_operator.nodes.fill_application.call_llm",
            return_value='["not", "a", "dict"]',
        ):
            result = _map_fields_with_llm(fields, resume, job)

        assert result == {}


# ---------------------------------------------------------------------------
# Unit tests: _fill_field
# ---------------------------------------------------------------------------


class TestFillField:
    @pytest.mark.asyncio
    async def test_fills_text_input(self) -> None:
        page = _mock_page()
        field = _text_field("name", "Full Name")
        await _fill_field(page, field, "John Doe", "/tmp/resume.pdf")
        page.fill.assert_called_once_with('[name="name"]', "John Doe")

    @pytest.mark.asyncio
    async def test_selects_dropdown_option(self) -> None:
        page = _mock_page()
        field = _select_field()
        await _fill_field(page, field, "United States", "/tmp/resume.pdf")
        page.select_option.assert_called_once_with('[name="country"]', label="United States")

    @pytest.mark.asyncio
    async def test_checks_checkbox_when_true(self) -> None:
        page = _mock_page()
        field = _checkbox_field()
        await _fill_field(page, field, "true", "/tmp/resume.pdf")
        page.check.assert_called_once_with('[name="agree_terms"]')

    @pytest.mark.asyncio
    async def test_unchecks_checkbox_when_false(self) -> None:
        page = _mock_page()
        field = _checkbox_field()
        await _fill_field(page, field, "false", "/tmp/resume.pdf")
        page.uncheck.assert_called_once_with('[name="agree_terms"]')

    @pytest.mark.asyncio
    async def test_uploads_resume_file(self) -> None:
        page = _mock_page()
        file_input = AsyncMock()
        page.query_selector = AsyncMock(return_value=file_input)
        field = _file_field()
        await _fill_field(page, field, "RESUME_FILE", "/tmp/resume.pdf")
        file_input.set_input_files.assert_called_once_with("/tmp/resume.pdf")

    @pytest.mark.asyncio
    async def test_skips_file_upload_without_resume_path(self) -> None:
        page = _mock_page()
        field = _file_field()
        await _fill_field(page, field, "RESUME_FILE", "")
        page.query_selector.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_fill_error_gracefully(self) -> None:
        page = _mock_page()
        page.fill = AsyncMock(side_effect=Exception("Element not found"))
        field = _text_field()
        # Should not raise
        await _fill_field(page, field, "value", "/tmp/resume.pdf")


# ---------------------------------------------------------------------------
# Unit tests: _find_and_click
# ---------------------------------------------------------------------------


class TestFindAndClick:
    @pytest.mark.asyncio
    async def test_clicks_first_visible_match(self) -> None:
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)

        page = _mock_page()
        page.query_selector = AsyncMock(return_value=mock_element)

        result = await _find_and_click(page, ['button[type="submit"]'])

        assert result is True
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_match(self) -> None:
        page = _mock_page()
        page.query_selector = AsyncMock(return_value=None)

        result = await _find_and_click(page, ['button[type="submit"]'])

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_hidden_elements(self) -> None:
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=False)

        page = _mock_page()
        page.query_selector = AsyncMock(return_value=mock_element)

        result = await _find_and_click(page, ['button[type="submit"]'])

        assert result is False


# ---------------------------------------------------------------------------
# Unit tests: _verify_submission
# ---------------------------------------------------------------------------


class TestVerifySubmission:
    @pytest.mark.asyncio
    async def test_detects_confirmation_via_heuristic(self) -> None:
        page = _mock_page()
        with patch(
            "apply_operator.nodes.fill_application.get_page_text",
            return_value="Thank you for your application! We have received your submission.",
        ):
            result = await _verify_submission(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_confirmation_via_llm(self) -> None:
        page = _mock_page()
        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Your profile has been saved. Our team will review shortly.",
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                return_value='{"page_type": "confirmation"}',
            ),
        ):
            result = await _verify_submission(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_non_confirmation(self) -> None:
        page = _mock_page()
        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Please fill out the following form.",
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                return_value='{"page_type": "form"}',
            ),
        ):
            result = await _verify_submission(page)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_page(self) -> None:
        page = _mock_page()
        with patch(
            "apply_operator.nodes.fill_application.get_page_text",
            return_value="",
        ):
            result = await _verify_submission(page)
        assert result is False


# ---------------------------------------------------------------------------
# Integration tests: fill_application node
# ---------------------------------------------------------------------------


SAMPLE_FORM_FIELDS: list[FormField] = [
    _text_field("name", "Full Name"),
    _text_field("email", "Email Address"),
    _file_field("resume"),
]

SAMPLE_LLM_MAPPING = json.dumps(
    {
        "name": "John Doe",
        "email": "john@example.com",
        "resume": "RESUME_FILE",
    }
)


class TestFillApplication:
    @pytest.mark.asyncio
    async def test_successful_single_page_application(self) -> None:
        state = _make_state()
        page = _mock_page()

        # Submit button exists
        submit_btn = AsyncMock()
        submit_btn.is_visible = AsyncMock(return_value=True)

        call_count = 0

        async def _query_selector(selector: str) -> AsyncMock | None:
            nonlocal call_count
            # For file upload query
            if selector.startswith('[name="resume"]'):
                file_input = AsyncMock()
                return file_input
            # For next-page buttons: return None (no next page)
            next_kws = ("Next", "Continue", "next", "continue")
            if any(kw in selector for kw in next_kws):
                return None
            # For submit button
            submit_kws = ("Submit", "Apply", "Send")
            if "submit" in selector.lower() or any(kw in selector for kw in submit_kws):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return submit_btn
                return None
            return None

        page.query_selector = _query_selector

        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.fill_application.get_form_fields",
                return_value=SAMPLE_FORM_FIELDS,
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                side_effect=[
                    SAMPLE_LLM_MAPPING,  # map_fields_with_llm
                    '{"page_type": "confirmation"}',  # verify_submission
                ],
            ),
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Thank you for applying!",
            ),
            patch(
                "apply_operator.nodes.fill_application.handle_captcha_if_present",
            ),
            patch(
                "apply_operator.nodes.fill_application.take_screenshot",
            ),
        ):
            result = await fill_application(state)

        assert result["current_job_index"] == 1
        assert result["total_applied"] == 1
        assert result["jobs"][0].applied is True

    @pytest.mark.asyncio
    async def test_multi_page_form(self) -> None:
        state = _make_state()
        page = _mock_page()

        page1_fields = [_text_field("name", "Full Name")]
        page2_fields = [_text_field("email", "Email")]

        form_fields_calls = [page1_fields, page2_fields]
        form_fields_idx = 0

        async def _get_form_fields(p: Any) -> list[FormField]:
            nonlocal form_fields_idx
            idx = form_fields_idx
            form_fields_idx += 1
            if idx < len(form_fields_calls):
                return form_fields_calls[idx]
            return []

        # Track button clicks
        next_btn = AsyncMock()
        next_btn.is_visible = AsyncMock(return_value=True)
        submit_btn = AsyncMock()
        submit_btn.is_visible = AsyncMock(return_value=True)

        click_phase = 0

        async def _query_selector(selector: str) -> AsyncMock | None:
            nonlocal click_phase
            # Page 1: next button exists
            if click_phase == 0 and ("Next" in selector or "Continue" in selector):
                click_phase = 1
                return next_btn
            # Page 2: submit button exists
            if click_phase == 1 and ("submit" in selector.lower() or "Submit" in selector):
                click_phase = 2
                return submit_btn
            return None

        page.query_selector = _query_selector

        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.fill_application.get_form_fields",
                side_effect=_get_form_fields,
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                side_effect=[
                    '{"name": "John Doe"}',
                    '{"email": "john@example.com"}',
                    '{"page_type": "confirmation"}',
                ],
            ),
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Thank you!",
            ),
            patch(
                "apply_operator.nodes.fill_application.handle_captcha_if_present",
            ),
            patch(
                "apply_operator.nodes.fill_application.take_screenshot",
            ),
        ):
            result = await fill_application(state)

        assert result["total_applied"] == 1
        assert result["jobs"][0].applied is True

    @pytest.mark.asyncio
    async def test_captcha_triggers_user_wait(self) -> None:
        state = _make_state()
        page = _mock_page()

        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.fill_application.get_form_fields",
                return_value=SAMPLE_FORM_FIELDS,
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                side_effect=[
                    SAMPLE_LLM_MAPPING,
                    '{"page_type": "confirmation"}',
                ],
            ),
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Thank you!",
            ),
            patch(
                "apply_operator.nodes.fill_application.handle_captcha_if_present",
            ) as mock_captcha,
            patch(
                "apply_operator.nodes.fill_application.take_screenshot",
            ),
        ):
            # Make submit button clickable
            submit_btn = AsyncMock()
            submit_btn.is_visible = AsyncMock(return_value=True)

            async def _qs(selector: str) -> AsyncMock | None:
                if "submit" in selector.lower():
                    return submit_btn
                return None

            page.query_selector = _qs

            await fill_application(state)

        # handle_captcha_if_present should be called at least twice
        # (pre-form and pre-submit)
        assert mock_captcha.call_count >= 2

    @pytest.mark.asyncio
    async def test_no_form_fields_advances_index(self) -> None:
        state = _make_state()
        page = _mock_page()

        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.fill_application.get_form_fields",
                return_value=[],
            ),
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Some random page",
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                return_value='{"page_type": "other"}',
            ),
            patch(
                "apply_operator.nodes.fill_application.handle_captcha_if_present",
            ),
            patch(
                "apply_operator.nodes.fill_application.take_screenshot",
            ),
        ):
            result = await fill_application(state)

        assert result["current_job_index"] == 1
        # Not applied because no form was filled
        assert result["jobs"][0].applied is not True

    @pytest.mark.asyncio
    async def test_exception_records_error_advances_index(self) -> None:
        state = _make_state()

        @asynccontextmanager
        async def _failing_session(url: str):  # type: ignore[no-untyped-def]
            raise ConnectionError("Browser launch failed")
            yield  # pragma: no cover

        with patch(
            "apply_operator.nodes.fill_application.get_page_with_session",
            side_effect=_failing_session,
        ):
            result = await fill_application(state)

        assert result["current_job_index"] == 1
        assert len(result["errors"]) == 1
        assert "Browser launch failed" in result["errors"][0]
        assert result["jobs"][0].error != ""

    @pytest.mark.asyncio
    async def test_file_upload_uses_resume_path(self) -> None:
        state = _make_state()
        page = _mock_page()

        file_input = AsyncMock()
        submit_btn = AsyncMock()
        submit_btn.is_visible = AsyncMock(return_value=True)

        async def _qs(selector: str) -> AsyncMock | None:
            if selector == '[name="resume"]':
                return file_input
            if "submit" in selector.lower():
                return submit_btn
            return None

        page.query_selector = _qs

        fields_with_file = [_file_field("resume")]

        with (
            patch(
                "apply_operator.nodes.fill_application.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.fill_application.get_form_fields",
                return_value=fields_with_file,
            ),
            patch(
                "apply_operator.nodes.fill_application.call_llm",
                side_effect=[
                    '{"resume": "RESUME_FILE"}',
                    '{"page_type": "confirmation"}',
                ],
            ),
            patch(
                "apply_operator.nodes.fill_application.get_page_text",
                return_value="Thank you!",
            ),
            patch(
                "apply_operator.nodes.fill_application.handle_captcha_if_present",
            ),
            patch(
                "apply_operator.nodes.fill_application.take_screenshot",
            ),
        ):
            await fill_application(state)

        file_input.set_input_files.assert_called_once_with("/tmp/resume.pdf")
