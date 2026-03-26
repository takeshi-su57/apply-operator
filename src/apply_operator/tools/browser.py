"""Playwright browser automation for job applications."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, async_playwright

from apply_operator.config import get_settings


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
