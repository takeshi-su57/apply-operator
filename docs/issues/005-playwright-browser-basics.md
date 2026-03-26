# [Feature]: Implement Playwright browser tool and helpers

**Labels:** `enhancement`, `priority:high`
**Depends on:** [001](001-project-setup-and-verify.md)

## Description

Implement and verify the browser automation tool (`tools/browser.py`) with Playwright. Add helper functions for common operations: extracting page text, getting links, taking screenshots. This is foundational for job searching (issue 006) and form filling (issue 009).

## Motivation

- Job applications require interacting with real web pages — Playwright controls a real browser
- Helper functions reduce boilerplate in every node that uses the browser
- Learning async Playwright patterns here avoids debugging them during complex node work

## Proposed Solution

- Verify existing `get_browser()` and `get_page()` context managers work
- Add helpers: `get_page_text(page)`, `get_page_links(page)`, `take_screenshot(page, name)`
- Create a manual test script (`scripts/test_browser.py`) to visually verify
- Write automated tests with mocked Playwright

### Key Playwright concepts

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto("https://example.com")
    title = await page.title()
    text = await page.text_content("body")
    await page.fill('input[name="email"]', "john@example.com")
    await page.click('button[type="submit"]')
    await page.screenshot(path="screenshot.png")
    await browser.close()
```

### Important: async nodes in LangGraph

LangGraph handles async nodes automatically:
```python
async def my_node(state: ApplicationState) -> dict:
    async with get_page() as page:
        await page.goto(url)
    return {"field": value}
```

## Alternatives Considered

- **Selenium** — older, slower, less reliable than Playwright
- **Puppeteer** — Node.js only, Playwright is its Python successor

## Acceptance Criteria

- [ ] `get_page()` opens and closes a browser cleanly
- [ ] `get_page_text(page)` returns visible text content
- [ ] `get_page_links(page)` returns list of `{href, text}` dicts
- [ ] `take_screenshot(page, name)` saves to `data/screenshots/`
- [ ] Both headless and headed mode work (`BROWSER_HEADLESS=true/false`)
- [ ] `scripts/test_browser.py` loads a page and prints the title
- [ ] Tests pass with mocked Playwright
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/browser.py` — add helper functions
- `scripts/test_browser.py` — create manual test
- `tests/test_browser.py` — create

## Related Issues

- Blocks [006](006-search-jobs-node.md) and [009](009-fill-application-node.md)
