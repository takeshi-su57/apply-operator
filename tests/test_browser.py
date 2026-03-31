"""Tests for browser automation tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from apply_operator.tools.browser import (
    LinkInfo,
    get_page,
    get_page_links,
    get_page_text,
    get_page_with_session,
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
