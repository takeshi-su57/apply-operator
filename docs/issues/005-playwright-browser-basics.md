# [Feature]: Implement Playwright browser tool with session persistence and user intervention

**Labels:** `enhancement`, `priority:high`
**Depends on:** [001](001-project-setup-and-verify.md)

## Description

Implement the browser automation tool (`tools/browser.py`) with Playwright. Beyond basic helpers, this must support **session persistence** (save/load cookies per domain) and a **user intervention flow** (pause automation, show browser, wait for user to handle login or CAPTCHA, then resume).

## Motivation

- Job sites require authentication — instead of managing per-site credentials, the agent detects login walls and lets the user log in manually
- Saved sessions (`data/sessions/<domain>.json`) avoid repeated manual logins across runs
- Bot detection (CAPTCHA, verification) is inevitable — the agent must gracefully hand off to the user
- Helper functions reduce boilerplate in every node that uses the browser

## Proposed Solution

### Session persistence

Use Playwright's `storage_state` to save/load cookies + localStorage per domain:

```python
from pathlib import Path

SESSIONS_DIR = Path("data/sessions")

def session_path(url: str) -> Path:
    """Get session file path for a domain."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    return SESSIONS_DIR / f"{domain}.json"

async def get_page_with_session(url: str) -> AsyncGenerator[Page, None]:
    """Create a page with saved session if available."""
    path = session_path(url)
    context_kwargs = {}
    if path.exists():
        context_kwargs["storage_state"] = str(path)
    # ... create context with kwargs
    yield page
    # Save session after use
    state = await context.storage_state()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))
```

### User intervention flow

When login or CAPTCHA is detected, pause and notify user via CLI:

```python
async def wait_for_user(page: Page, message: str) -> None:
    """Show browser to user, print message, wait for Enter to resume."""
    console.print(f"[bold yellow]{message}[/bold yellow]")
    console.print("[dim]Complete the action in the browser, then press Enter...[/dim]")
    await asyncio.get_event_loop().run_in_executor(None, input)
```

### Browser helpers

- `get_page_text(page)` — extract visible text content
- `get_page_links(page)` — return list of `{href, text}` dicts
- `take_screenshot(page, name)` — save to `data/screenshots/`

### Important: headed mode for auth

During login/CAPTCHA flows, the browser **must** be visible (`headless=False`) so the user can interact. The `get_page_with_session` context manager should launch in headed mode when user intervention might be needed.

## Alternatives Considered

- **Per-site credentials in config** — fragile, can't handle Google OAuth or 2FA
- **Automated CAPTCHA solving** — unreliable, may violate site terms
- **No session persistence** — forces manual login every run

## Acceptance Criteria

- [x] `get_page()` opens and closes a browser cleanly
- [x] `get_page_with_session(url)` loads saved session if available
- [x] Sessions saved to `data/sessions/<domain>.json` after page use
- [x] Expired sessions detected (login wall still present after loading session)
- [x] `wait_for_user(page, message)` pauses automation and shows browser
- [x] `get_page_text(page)` returns visible text content
- [x] `get_page_links(page)` returns list of `{href, text}` dicts
- [x] `take_screenshot(page, name)` saves to `data/screenshots/`
- [x] Both headless and headed mode work (`BROWSER_HEADLESS=true/false`)
- [x] Tests pass with mocked Playwright
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/browser.py` — session persistence, user intervention, helpers
- `scripts/test_browser.py` — create manual test
- `tests/test_browser.py` — create

## Related Issues

- Blocks [006](006-search-jobs-node.md) and [009](009-fill-application-node.md)
