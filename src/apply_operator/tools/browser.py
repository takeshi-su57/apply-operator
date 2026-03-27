"""Playwright browser automation for job applications."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from rich.console import Console

from apply_operator.config import get_settings

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("data/sessions")
SCREENSHOTS_DIR = Path("data/screenshots")


class LinkInfo(TypedDict):
    """Typed dict for page link information."""

    href: str
    text: str


def session_path(url: str) -> Path:
    """Get session file path for a URL's domain.

    Args:
        url: Full URL to extract domain from.

    Returns:
        Path to the session JSON file for the domain.
    """
    domain = urlparse(url).netloc
    return SESSIONS_DIR / f"{domain}.json"


@asynccontextmanager
async def get_browser() -> AsyncGenerator[Browser, None]:
    """Create and yield a Playwright browser instance."""
    settings = get_settings()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.browser_headless)
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
async def _get_browser_headed() -> AsyncGenerator[Browser, None]:
    """Create a headed (visible) browser instance for user intervention."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def get_page_with_session(url: str) -> AsyncGenerator[Page, None]:
    """Create a page with saved session cookies if available.

    Always launches in headed mode so the user can intervene for login/CAPTCHA.
    Saves the session (cookies + localStorage) on exit.

    Args:
        url: URL to load session for (session is keyed by domain).
    """
    path = session_path(url)
    context: BrowserContext | None = None
    page: Page | None = None

    async with _get_browser_headed() as browser:
        try:
            if path.exists():
                logger.info("Loading saved session from %s", path)
                context = await browser.new_context(storage_state=str(path))
            else:
                context = await browser.new_context()

            page = await context.new_page()
            yield page
        finally:
            # Save session before cleanup
            if context is not None:
                try:
                    state = await context.storage_state()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(state), encoding="utf-8")
                    logger.info("Session saved to %s", path)
                except Exception:
                    logger.warning("Failed to save session to %s", path, exc_info=True)
            if page is not None:
                await page.close()
            if context is not None:
                await context.close()


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
