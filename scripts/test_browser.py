"""Manual browser test script.

Run with:
    python scripts/test_browser.py

Requires Playwright browsers installed:
    playwright install chromium
"""

import asyncio

from apply_operator.tools.browser import (
    get_page,
    get_page_links,
    get_page_text,
    get_page_with_session,
    session_path,
    take_screenshot,
    wait_for_user,
)


async def test_basic_page() -> None:
    """Test basic page creation and helper functions."""
    print("--- Test 1: get_page + helpers ---")
    async with get_page() as page:
        await page.goto("https://example.com")

        text = await get_page_text(page)
        print(f"Page text length: {len(text)} chars")
        print(f"First 100 chars: {text[:100]!r}")

        links = await get_page_links(page)
        print(f"Links found: {len(links)}")
        for link in links:
            print(f"  - {link['text']}: {link['href']}")

        path = await take_screenshot(page, "example_com")
        print(f"Screenshot saved: {path}")

    print("Test 1 passed!\n")


async def test_session_persistence() -> None:
    """Test session save/load with user intervention."""
    url = "https://example.com"
    print("--- Test 2: get_page_with_session ---")
    print(f"Session file: {session_path(url)}")

    async with get_page_with_session(url) as page:
        await page.goto(url)
        text = await get_page_text(page)
        print(f"Page loaded, text length: {len(text)} chars")
        await wait_for_user(page, "Browser is open. Press Enter to save session and close.")

    print(f"Session saved to: {session_path(url)}")
    print("Run again to test session loading.\n")


async def main() -> None:
    """Run all manual browser tests."""
    print("=== Manual Browser Tests ===\n")
    await test_basic_page()
    await test_session_persistence()
    print("=== All tests complete ===")


if __name__ == "__main__":
    asyncio.run(main())
