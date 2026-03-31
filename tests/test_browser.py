"""Tests for browser automation tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apply_operator.tools.browser import (
    LinkInfo,
    detect_captcha,
    get_form_fields,
    get_page,
    get_page_links,
    get_page_text,
    get_page_with_session,
    handle_captcha_if_present,
    session_path,
    take_screenshot,
    wait_for_user,
)


class TestSessionPath:
    """Tests for session_path URL-to-path mapping."""

    def test_returns_path_for_simple_url(self) -> None:
        result = session_path("https://linkedin.com/jobs")
        assert result == Path("data/sessions/linkedin.com")

    def test_handles_url_with_port(self) -> None:
        result = session_path("http://localhost:8080/page")
        assert result == Path("data/sessions/localhost:8080")

    def test_handles_subdomain(self) -> None:
        result = session_path("https://jobs.lever.co/company")
        assert result == Path("data/sessions/jobs.lever.co")

    def test_handles_url_with_path_and_query(self) -> None:
        result = session_path("https://example.com/path?q=1")
        assert result == Path("data/sessions/example.com")


class TestGetBrowser:
    """Tests for get_browser context manager."""

    @patch("apply_operator.tools.browser.get_settings")
    @patch("apply_operator.tools.browser.async_playwright")
    async def test_launches_chromium_with_headless_setting(
        self, mock_playwright: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.browser_headless = True
        mock_browser = AsyncMock()
        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        from apply_operator.tools.browser import get_browser

        async with get_browser() as browser:
            assert browser is mock_browser

        mock_pw.chromium.launch.assert_called_once_with(
            headless=True,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )

    @patch("apply_operator.tools.browser.get_settings")
    @patch("apply_operator.tools.browser.async_playwright")
    async def test_closes_browser_on_exit(
        self, mock_playwright: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.browser_headless = True
        mock_browser = AsyncMock()
        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        from apply_operator.tools.browser import get_browser

        async with get_browser():
            pass

        mock_browser.close.assert_awaited_once()


class TestGetPage:
    """Tests for get_page context manager."""

    @patch("apply_operator.tools.browser.get_browser")
    async def test_creates_and_yields_page(self, mock_get_browser: MagicMock) -> None:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_get_browser.return_value.__aenter__.return_value = mock_browser

        async with get_page() as page:
            assert page is mock_page

        mock_browser.new_page.assert_awaited_once()

    @patch("apply_operator.tools.browser.get_browser")
    async def test_closes_page_on_exit(self, mock_get_browser: MagicMock) -> None:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_get_browser.return_value.__aenter__.return_value = mock_browser

        async with get_page():
            pass

        mock_page.close.assert_awaited_once()


class TestGetPageWithSession:
    """Tests for get_page_with_session context manager.

    The implementation uses Playwright's launch_persistent_context with a
    per-domain user data directory. Sessions are preserved by the browser
    profile, not by explicit JSON storage_state files.
    """

    @patch("apply_operator.tools.browser.async_playwright")
    async def test_launches_persistent_context_with_domain_dir(
        self, mock_playwright: MagicMock, tmp_path: Path
    ) -> None:
        user_data_dir = tmp_path / "example.com"
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.pages = [mock_page]

        mock_pw = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        with patch("apply_operator.tools.browser.session_path", return_value=user_data_dir):
            async with get_page_with_session("https://example.com") as page:
                assert page is mock_page

        mock_pw.chromium.launch_persistent_context.assert_awaited_once_with(
            user_data_dir=str(user_data_dir),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )

    @patch("apply_operator.tools.browser.async_playwright")
    async def test_creates_user_data_directory(
        self, mock_playwright: MagicMock, tmp_path: Path
    ) -> None:
        user_data_dir = tmp_path / "deep" / "nested" / "example.com"
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.pages = [mock_page]

        mock_pw = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        with patch("apply_operator.tools.browser.session_path", return_value=user_data_dir):
            async with get_page_with_session("https://example.com"):
                pass

        assert user_data_dir.exists()

    @patch("apply_operator.tools.browser.async_playwright")
    async def test_creates_new_page_when_context_has_none(
        self, mock_playwright: MagicMock, tmp_path: Path
    ) -> None:
        user_data_dir = tmp_path / "example.com"
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.pages = []  # no existing pages
        mock_context.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        with patch("apply_operator.tools.browser.session_path", return_value=user_data_dir):
            async with get_page_with_session("https://example.com") as page:
                assert page is mock_page

        mock_context.new_page.assert_awaited_once()

    @patch("apply_operator.tools.browser.async_playwright")
    async def test_reuses_existing_page_from_context(
        self, mock_playwright: MagicMock, tmp_path: Path
    ) -> None:
        user_data_dir = tmp_path / "example.com"
        mock_existing_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.pages = [mock_existing_page]

        mock_pw = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        with patch("apply_operator.tools.browser.session_path", return_value=user_data_dir):
            async with get_page_with_session("https://example.com") as page:
                assert page is mock_existing_page

        mock_context.new_page.assert_not_awaited()

    @patch("apply_operator.tools.browser.async_playwright")
    async def test_closes_context_on_exit(self, mock_playwright: MagicMock, tmp_path: Path) -> None:
        user_data_dir = tmp_path / "example.com"
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.pages = [mock_page]

        mock_pw = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        with patch("apply_operator.tools.browser.session_path", return_value=user_data_dir):
            async with get_page_with_session("https://example.com"):
                pass

        mock_context.close.assert_awaited_once()


class TestWaitForUser:
    """Tests for wait_for_user function."""

    @patch("apply_operator.tools.browser.Console")
    async def test_prints_message_and_waits(self, mock_console_cls: MagicMock) -> None:
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        mock_page = AsyncMock()

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            await wait_for_user(mock_page, "Please log in")

        # Verify message was printed
        calls = mock_console.print.call_args_list
        assert any("Please log in" in str(c) for c in calls)
        assert len(calls) == 2  # message + instruction


class TestGetPageText:
    """Tests for get_page_text helper."""

    async def test_returns_inner_text(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = "Hello World"
        result = await get_page_text(mock_page)
        assert result == "Hello World"

    async def test_returns_empty_string_on_error(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.side_effect = Exception("page crashed")
        result = await get_page_text(mock_page)
        assert result == ""

    async def test_calls_evaluate_with_js(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = ""
        await get_page_text(mock_page)
        mock_page.evaluate.assert_awaited_once()
        js_code = mock_page.evaluate.call_args[0][0]
        assert "innerText" in js_code


class TestGetPageLinks:
    """Tests for get_page_links helper."""

    async def test_returns_list_of_link_dicts(self) -> None:
        mock_page = AsyncMock()
        expected: list[LinkInfo] = [
            {"href": "https://example.com", "text": "Example"},
            {"href": "https://other.com/page", "text": "Other Page"},
        ]
        mock_page.evaluate.return_value = expected
        result = await get_page_links(mock_page)
        assert result == expected

    async def test_returns_empty_list_on_error(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.side_effect = Exception("page crashed")
        result = await get_page_links(mock_page)
        assert result == []

    async def test_calls_evaluate_with_queryselector(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = []
        await get_page_links(mock_page)
        js_code = mock_page.evaluate.call_args[0][0]
        assert "querySelectorAll" in js_code
        assert "a[href]" in js_code


class TestTakeScreenshot:
    """Tests for take_screenshot helper."""

    async def test_saves_screenshot_and_returns_path(self, tmp_path: Path) -> None:
        mock_page = AsyncMock()
        screenshots_dir = tmp_path / "screenshots"

        with patch("apply_operator.tools.browser.SCREENSHOTS_DIR", screenshots_dir):
            result = await take_screenshot(mock_page, "test_shot")

        mock_page.screenshot.assert_awaited_once()
        assert result == screenshots_dir / "test_shot.png"

    async def test_creates_screenshots_directory(self, tmp_path: Path) -> None:
        mock_page = AsyncMock()
        screenshots_dir = tmp_path / "new_dir" / "screenshots"

        with patch("apply_operator.tools.browser.SCREENSHOTS_DIR", screenshots_dir):
            await take_screenshot(mock_page, "test")

        assert screenshots_dir.exists()

    async def test_passes_path_to_playwright(self, tmp_path: Path) -> None:
        mock_page = AsyncMock()
        screenshots_dir = tmp_path / "screenshots"

        with patch("apply_operator.tools.browser.SCREENSHOTS_DIR", screenshots_dir):
            await take_screenshot(mock_page, "capture")

        call_kwargs = mock_page.screenshot.call_args[1]
        assert call_kwargs["path"] == str(screenshots_dir / "capture.png")


class TestDetectCaptcha:
    """Tests for CAPTCHA detection."""

    @pytest.mark.asyncio
    async def test_detects_captcha_via_selector(self) -> None:
        mock_page = AsyncMock()
        visible_element = AsyncMock()
        visible_element.is_visible.return_value = True
        mock_page.query_selector.return_value = visible_element

        result = await detect_captcha(mock_page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_captcha_via_text(self) -> None:
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        mock_page.evaluate.return_value = "Please verify you are human to continue"

        result = await detect_captcha(mock_page)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_captcha(self) -> None:
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        mock_page.evaluate.return_value = "Welcome to our job board"

        result = await detect_captcha(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_selector_exception(self) -> None:
        mock_page = AsyncMock()
        mock_page.query_selector.side_effect = Exception("selector error")
        mock_page.evaluate.return_value = "Normal page"

        result = await detect_captcha(mock_page)
        assert result is False


class TestHandleCaptchaIfPresent:
    """Tests for handle_captcha_if_present."""

    @pytest.mark.asyncio
    async def test_calls_wait_when_captcha_detected(self) -> None:
        mock_page = AsyncMock()

        with (
            patch("apply_operator.tools.browser.detect_captcha", return_value=True),
            patch("apply_operator.tools.browser.wait_for_user") as mock_wait,
            patch("apply_operator.tools.browser.wait_for_page_ready"),
        ):
            await handle_captcha_if_present(mock_page)
            mock_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_noop_when_no_captcha(self) -> None:
        mock_page = AsyncMock()

        with (
            patch("apply_operator.tools.browser.detect_captcha", return_value=False),
            patch("apply_operator.tools.browser.wait_for_user") as mock_wait,
        ):
            await handle_captcha_if_present(mock_page)
            mock_wait.assert_not_called()


class TestGetFormFields:
    """Tests for form field extraction."""

    @pytest.mark.asyncio
    async def test_returns_fields_from_evaluate(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = [
            {
                "tag": "input",
                "field_type": "text",
                "name": "first_name",
                "label": "First Name",
                "required": True,
                "selector": "#first_name",
                "options": [],
            },
        ]

        fields = await get_form_fields(mock_page)
        assert len(fields) == 1
        assert fields[0]["name"] == "first_name"
        assert fields[0]["label"] == "First Name"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.side_effect = Exception("JS error")

        fields = await get_form_fields(mock_page)
        assert fields == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_fields(self) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = []

        fields = await get_form_fields(mock_page)
        assert fields == []
