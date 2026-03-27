"""Playwright browser automation for job applications."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright
from rich.console import Console

from apply_operator.config import get_settings

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("data/sessions")
SCREENSHOTS_DIR = Path("data/screenshots")

_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
]


class LinkInfo(TypedDict):
    """Typed dict for page link information."""

    href: str
    text: str


def session_path(url: str) -> Path:
    """Get session file path for a URL's domain.

    Args:
        url: Full URL to extract domain from.

    Returns:
        Path to the session directory for the domain.
    """
    domain = urlparse(url).netloc
    return SESSIONS_DIR / domain


@asynccontextmanager
async def get_browser() -> AsyncGenerator[Browser, None]:
    """Create and yield a Playwright browser instance."""
    settings = get_settings()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=settings.browser_headless,
            channel="chrome",
            args=_STEALTH_ARGS,
        )
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def get_page() -> AsyncGenerator[Page, None]:
    """Create and yield a browser page (convenience wrapper)."""
    async with get_browser() as browser:
        page = await browser.new_page()
        try:
            yield page
        finally:
            await page.close()


@asynccontextmanager
async def get_page_with_session(url: str) -> AsyncGenerator[Page, None]:
    """Create a page with a persistent browser profile for the domain.

    Uses launch_persistent_context with a per-domain user data directory,
    making the browser indistinguishable from a normal Chrome session.
    Always launches in headed mode so the user can intervene for login/CAPTCHA.

    Args:
        url: URL to load session for (session directory is keyed by domain).
    """
    user_data_dir = session_path(url)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            channel="chrome",
            args=_STEALTH_ARGS,
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            yield page
        finally:
            await context.close()
            logger.info("Session saved to %s", user_data_dir)


async def wait_for_page_ready(
    page: Page,
    *,
    settle_ms: int = 500,
    timeout_ms: int = 10000,
) -> None:
    """Wait for a page to finish rendering dynamic content.

    Strategy:
    1. Wait for network idle (no in-flight requests for 500ms).
    2. Poll page text length until it stabilizes — catches skeleton screens,
       lazy-loaded lists, and JS-rendered content that appears after network idle.

    Args:
        page: Playwright page to wait on.
        settle_ms: How long (ms) the text length must stay unchanged to consider
            the page stable. Default 500ms.
        timeout_ms: Maximum total wait time. Default 10s.
    """
    # Step 1: wait for network to quiet down
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        logger.debug("networkidle timed out, proceeding to content stability check")

    # Step 2: poll text length until stable
    prev_length = 0
    stable_since = 0.0
    elapsed = 0.0
    poll_interval = 0.25  # seconds

    while elapsed < timeout_ms / 1000:
        text = await page.evaluate("() => (document.body.innerText || '').length")
        now = asyncio.get_event_loop().time()

        if text != prev_length:
            prev_length = text
            stable_since = now
        elif (now - stable_since) >= settle_ms / 1000:
            logger.debug("Page content stable at %d chars after %.1fs", text, elapsed)
            return

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    logger.debug("Page ready timeout after %.1fs, proceeding with %d chars", elapsed, prev_length)


async def wait_for_user(page: Page, message: str) -> None:
    """Pause automation and wait for user to complete an action in the browser.

    The browser must be visible (headed mode) for the user to interact.

    Args:
        page: The current browser page (kept open for user interaction).
        message: Message to display to the user.
    """
    console = Console()
    console.print(f"[bold yellow]{message}[/bold yellow]")
    console.print("[dim]Complete the action in the browser, then press Enter...[/dim]")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input)


async def get_page_text(page: Page) -> str:
    """Extract visible text content from a page.

    Args:
        page: Playwright page to extract text from.

    Returns:
        Visible text content, or empty string on error.
    """
    try:
        text: str = await page.evaluate("() => document.body.innerText || ''")
        return text
    except Exception:
        logger.warning("Failed to extract page text", exc_info=True)
        return ""


async def get_page_links(page: Page) -> list[LinkInfo]:
    """Extract all links from a page.

    Args:
        page: Playwright page to extract links from.

    Returns:
        List of LinkInfo dicts with href and text keys.
    """
    try:
        links: list[LinkInfo] = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href,
                text: (a.textContent || '').trim()
            }))"""
        )
        return links
    except Exception:
        logger.warning("Failed to extract page links", exc_info=True)
        return []


async def take_screenshot(page: Page, name: str) -> Path:
    """Take a screenshot and save to data/screenshots/.

    Args:
        page: Playwright page to screenshot.
        name: Screenshot name (without extension).

    Returns:
        Path to the saved screenshot file.
    """
    path = SCREENSHOTS_DIR / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path))
    logger.info("Screenshot saved: %s", path)
    return path
