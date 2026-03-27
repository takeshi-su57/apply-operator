"""Tests for browser automation tools."""

import json
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
        assert result == Path("data/sessions/linkedin.com.json")

    def test_handles_url_with_port(self) -> None:
        result = session_path("http://localhost:8080/page")
        assert result == Path("data/sessions/localhost:8080.json")

    def test_handles_subdomain(self) -> None:
        result = session_path("https://jobs.lever.co/company")
        assert result == Path("data/sessions/jobs.lever.co.json")

    def test_handles_url_with_path_and_query(self) -> None:
        result = session_path("https://example.com/path?q=1")
        assert result == Path("data/sessions/example.com.json")


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

        mock_pw.chromium.launch.assert_called_once_with(headless=True)

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
    """Tests for get_page_with_session context manager."""

    @patch("apply_operator.tools.browser._get_browser_headed")
    async def test_loads_existing_session(
        self, mock_browser_headed: MagicMock, tmp_path: Path
    ) -> None:
        # Create a session file
        session_file = tmp_path / "example.com.json"
        session_data = {"cookies": [{"name": "sid", "value": "abc"}]}
        session_file.write_text(json.dumps(session_data))

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = session_data
        mock_browser_headed.return_value.__aenter__.return_value = mock_browser

        with patch("apply_operator.tools.browser.session_path", return_value=session_file):
            async with get_page_with_session("https://example.com") as page:
                assert page is mock_page

        mock_browser.new_context.assert_awaited_once_with(storage_state=str(session_file))

    @patch("apply_operator.tools.browser._get_browser_headed")
    async def test_creates_context_without_session(
        self, mock_browser_headed: MagicMock, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "new-site.com.json"  # Does not exist

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = {}
        mock_browser_headed.return_value.__aenter__.return_value = mock_browser

        with patch("apply_operator.tools.browser.session_path", return_value=session_file):
            async with get_page_with_session("https://new-site.com") as page:
                assert page is mock_page

        mock_browser.new_context.assert_awaited_once_with()

    @patch("apply_operator.tools.browser._get_browser_headed")
    async def test_saves_session_on_exit(
        self, mock_browser_headed: MagicMock, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "sessions" / "example.com.json"
        saved_state = {"cookies": [{"name": "token", "value": "xyz"}]}

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = saved_state
        mock_browser_headed.return_value.__aenter__.return_value = mock_browser

        with patch("apply_operator.tools.browser.session_path", return_value=session_file):
            async with get_page_with_session("https://example.com"):
                pass

        assert session_file.exists()
        written = json.loads(session_file.read_text())
        assert written == saved_state

    @patch("apply_operator.tools.browser._get_browser_headed")
    async def test_creates_session_directory(
        self, mock_browser_headed: MagicMock, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "deep" / "nested" / "example.com.json"

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = {}
        mock_browser_headed.return_value.__aenter__.return_value = mock_browser

        with patch("apply_operator.tools.browser.session_path", return_value=session_file):
            async with get_page_with_session("https://example.com"):
                pass

        assert session_file.parent.exists()

    @patch("apply_operator.tools.browser._get_browser_headed")
    async def test_closes_page_and_context_on_exit(
        self, mock_browser_headed: MagicMock, tmp_path: Path
    ) -> None:
        session_file = tmp_path / "example.com.json"

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = {}
        mock_browser_headed.return_value.__aenter__.return_value = mock_browser

        with patch("apply_operator.tools.browser.session_path", return_value=session_file):
            async with get_page_with_session("https://example.com"):
                pass

        mock_page.close.assert_awaited_once()
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
