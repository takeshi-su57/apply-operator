"""Tests for the search_jobs node."""

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from apply_operator.nodes.search_jobs import (
    _detect_login_required,
    _extract_jobs_from_page,
    _find_next_page,
    search_jobs,
)
from apply_operator.state import ApplicationState


def _make_state(**kwargs: Any) -> ApplicationState:
    """Create an ApplicationState with sensible defaults."""
    defaults: dict[str, Any] = {
        "resume_path": "test.pdf",
        "job_urls": ["https://example.com/jobs"],
    }
    defaults.update(kwargs)
    return ApplicationState(**defaults)


def _mock_page(url: str = "https://example.com/jobs", text: str = "") -> AsyncMock:
    """Create a mock Playwright page."""
    page = AsyncMock()
    page.url = url
    page.goto = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock()

    async def _get_text() -> str:
        return text

    # Patch get_page_text to return our text via the module-level function
    return page


@asynccontextmanager
async def _fake_session(page: AsyncMock):  # type: ignore[no-untyped-def]
    """Fake get_page_with_session context manager."""
    yield page


SAMPLE_LLM_RESPONSE = json.dumps(
    [
        {
            "title": "Python Developer",
            "company": "TechCo",
            "description": "Build cool stuff",
            "location": "Remote",
            "apply_url": "https://example.com/jobs/1",
        },
        {
            "title": "Data Engineer",
            "company": "DataCo",
            "description": "Process data",
            "location": "NYC",
            "apply_url": "https://example.com/jobs/2",
        },
    ]
)


class TestDetectLoginRequired:
    """Tests for _detect_login_required."""

    @pytest.mark.asyncio
    async def test_detects_login_url(self) -> None:
        page = AsyncMock()
        page.url = "https://example.com/login"
        with patch(
            "apply_operator.nodes.search_jobs.get_page_text",
            return_value="Welcome to our site",
        ):
            assert await _detect_login_required(page) is True

    @pytest.mark.asyncio
    async def test_detects_signin_in_page_text(self) -> None:
        page = AsyncMock()
        page.url = "https://example.com/page"
        with patch(
            "apply_operator.nodes.search_jobs.get_page_text",
            return_value="Please sign in to continue",
        ):
            assert await _detect_login_required(page) is True

    @pytest.mark.asyncio
    async def test_returns_false_for_normal_page(self) -> None:
        page = AsyncMock()
        page.url = "https://example.com/jobs"
        with patch(
            "apply_operator.nodes.search_jobs.get_page_text",
            return_value="Software Engineer - Remote - Apply Now",
        ):
            assert await _detect_login_required(page) is False


class TestExtractJobsFromPage:
    """Tests for _extract_jobs_from_page."""

    @pytest.mark.asyncio
    async def test_extracts_jobs_from_valid_response(self) -> None:
        page = AsyncMock()
        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Job listings page content",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=SAMPLE_LLM_RESPONSE,
            ),
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert len(jobs) == 2
        assert jobs[0].title == "Python Developer"
        assert jobs[0].company == "TechCo"
        assert jobs[0].url == "https://example.com/jobs/1"
        assert jobs[1].title == "Data Engineer"
        assert jobs[1].location == "NYC"

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_page(self) -> None:
        page = AsyncMock()
        with patch(
            "apply_operator.nodes.search_jobs.get_page_text",
            return_value="",
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self) -> None:
        page = AsyncMock()
        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Some page text",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value="not valid json {{{",
            ),
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self) -> None:
        wrapped = f"```json\n{SAMPLE_LLM_RESPONSE}\n```"
        page = AsyncMock()
        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Job listings",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=wrapped,
            ),
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_uses_source_url_when_apply_url_missing(self) -> None:
        response = json.dumps([{"title": "Dev", "company": "Co"}])
        page = AsyncMock()
        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Page text",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=response,
            ),
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert len(jobs) == 1
        assert jobs[0].url == "https://example.com/jobs"

    @pytest.mark.asyncio
    async def test_handles_non_list_response(self) -> None:
        page = AsyncMock()
        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Page text",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value='{"title": "Dev"}',
            ),
        ):
            jobs = await _extract_jobs_from_page(page, "https://example.com/jobs")

        assert jobs == []


class TestFindNextPage:
    """Tests for _find_next_page."""

    @pytest.mark.asyncio
    async def test_clicks_visible_next_button(self) -> None:
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)

        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=mock_element)

        result = await _find_next_page(page)

        assert result is True
        mock_element.click.assert_called_once()
        page.wait_for_load_state.assert_called_once_with("networkidle")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_pagination(self) -> None:
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)

        result = await _find_next_page(page)

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_hidden_elements(self) -> None:
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=False)

        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=mock_element)

        result = await _find_next_page(page)

        assert result is False


class TestSearchJobs:
    """Integration tests for the search_jobs node."""

    @pytest.mark.asyncio
    async def test_extracts_jobs_from_single_url(self) -> None:
        state = _make_state(job_urls=["https://example.com/jobs"])
        page = AsyncMock()
        page.url = "https://example.com/jobs"
        page.query_selector = AsyncMock(return_value=None)

        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Job listings here",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=SAMPLE_LLM_RESPONSE,
            ),
        ):
            result = await search_jobs(state)

        assert len(result["jobs"]) == 2
        assert result["current_job_index"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_handles_multiple_urls(self) -> None:
        state = _make_state(job_urls=["https://example.com/jobs", "https://other.com/careers"])
        page = AsyncMock()
        page.url = "https://example.com/jobs"
        page.query_selector = AsyncMock(return_value=None)

        single_job = json.dumps([{"title": "Dev", "company": "Co"}])

        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Jobs page",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=single_job,
            ),
        ):
            result = await search_jobs(state)

        assert len(result["jobs"]) == 2  # 1 job per URL

    @pytest.mark.asyncio
    async def test_login_detection_triggers_wait(self) -> None:
        state = _make_state(job_urls=["https://example.com/login"])
        page = AsyncMock()
        page.url = "https://example.com/login"
        page.query_selector = AsyncMock(return_value=None)

        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Please sign in",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value="[]",
            ),
            patch(
                "apply_operator.nodes.search_jobs.wait_for_user",
            ) as mock_wait,
        ):
            await search_jobs(state)

        mock_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_follows_pagination(self) -> None:
        state = _make_state(job_urls=["https://example.com/jobs"])
        page = AsyncMock()
        page.url = "https://example.com/jobs"

        mock_next = AsyncMock()
        mock_next.is_visible = AsyncMock(return_value=True)

        # First round of selectors (6 total): first one returns element (paginate).
        # Second round: all return None (stop).
        call_count = 0

        async def _query_selector(selector: str) -> AsyncMock | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_next  # First selector on first page -> click "Next"
            return None  # Everything else -> no match

        page.query_selector = _query_selector

        single_job = json.dumps([{"title": "Dev", "company": "Co"}])

        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_with_session",
                side_effect=lambda url: _fake_session(page),
            ),
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Jobs page",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=single_job,
            ),
        ):
            result = await search_jobs(state)

        # Should have jobs from 2 pages
        assert len(result["jobs"]) == 2

    @pytest.mark.asyncio
    async def test_failing_url_records_error_continues(self) -> None:
        state = _make_state(job_urls=["https://bad.com/jobs", "https://good.com/jobs"])
        page = AsyncMock()
        page.url = "https://good.com/jobs"
        page.query_selector = AsyncMock(return_value=None)

        call_count = 0

        @asynccontextmanager
        async def _session(url: str):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection refused")
            yield page

        single_job = json.dumps([{"title": "Dev", "company": "Co"}])

        with (
            patch(
                "apply_operator.nodes.search_jobs.get_page_with_session",
                side_effect=_session,
            ),
            patch(
                "apply_operator.nodes.search_jobs.get_page_text",
                return_value="Jobs",
            ),
            patch(
                "apply_operator.nodes.search_jobs.call_llm",
                return_value=single_job,
            ),
        ):
            result = await search_jobs(state)

        assert len(result["jobs"]) == 1  # Only good URL produced jobs
        assert len(result["errors"]) == 1
        assert "bad.com" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_empty_urls_returns_empty(self) -> None:
        state = _make_state(job_urls=[])
        result = await search_jobs(state)

        assert result["jobs"] == []
        assert result["current_job_index"] == 0
        assert result["errors"] == []
