# [Feature]: Implement search_jobs node with real-user browsing flow

**Labels:** `enhancement`, `priority:high`
**Depends on:** [005](005-playwright-browser-basics.md)

## Description

Implement the `search_jobs` node that visits each job site URL, handles authentication (via session or user intervention), browses job listings like a real user, evaluates each one, and handles pagination to discover all available jobs.

## Motivation

- Users provide raw URLs to job boards or company career pages
- The agent must navigate like a real user: detect login walls, browse listings, click through pages
- LLM-assisted extraction adapts to any site layout without hardcoded selectors
- Pagination handling ensures we don't miss jobs on multi-page results

## Proposed Solution

### Authentication-aware browsing flow

```
1. Load saved session for domain (if exists)
2. Visit job site URL
3. Detect: logged in or login required?
   → Login required → Switch to headed mode, prompt user to log in
   → After login → Save session, continue
   → Already logged in → Continue
4. Find job listings on the page
5. Extract job details using LLM
6. Check for pagination / "Load more" button
   → Found → Navigate to next page, repeat from step 4
   → Not found → Done with this URL
7. Repeat for next URL
```

### Login detection

Use LLM or heuristics to detect login walls:

```python
async def detect_login_required(page: Page) -> bool:
    """Check if the current page is a login wall."""
    text = await get_page_text(page)
    url = page.url
    # Heuristic: URL contains login/signin, or page has login form
    login_indicators = ["sign in", "log in", "login", "signin"]
    return (
        any(indicator in url.lower() for indicator in login_indicators)
        or any(indicator in text.lower()[:500] for indicator in login_indicators)
    )
```

### Job listing extraction

Use LLM to understand arbitrary page layouts:

```python
async def extract_jobs_from_page(page: Page, url: str) -> list[JobListing]:
    text = await get_page_text(page)
    llm = get_llm()
    response = llm.invoke(EXTRACT_JOBS.format(page_text=text[:8000], url=url))
    listings = json.loads(response.content)
    return [JobListing(url=item.get("apply_url", url), **item) for item in listings]
```

### Pagination handling

After processing all jobs on current page, detect and follow pagination:

```python
async def find_next_page(page: Page) -> bool:
    """Click next page / load more if available. Returns True if navigated."""
    text = await get_page_text(page)
    # Use LLM to identify pagination element, or check common selectors
    next_selectors = [
        'a[aria-label="Next"]', 'a:text("Next")', 'button:text("Load more")',
        'button:text("Show more")', '[class*="next"]', '[class*="pagination"] a:last-child',
    ]
    for selector in next_selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            await element.click()
            await page.wait_for_load_state("networkidle")
            return True
    return False
```

### New prompt needed

Add `EXTRACT_JOBS` to `prompts/job_matching.py`:
- Input: page text + source URL
- Output: JSON array of `{title, company, description, location, apply_url}`

### Async node

```python
async def search_jobs(state: ApplicationState) -> dict[str, Any]:
    all_jobs: list[JobListing] = []
    errors = list(state.errors)

    for url in state.job_urls:
        try:
            async with get_page_with_session(url) as page:
                await page.goto(url, timeout=30000)

                # Handle authentication
                if await detect_login_required(page):
                    await wait_for_user(page, f"Login required at {url}. Please log in.")

                # Extract jobs from current page + pagination
                while True:
                    page_jobs = await extract_jobs_from_page(page, url)
                    all_jobs.extend(page_jobs)
                    if not await find_next_page(page):
                        break
        except Exception as e:
            errors.append(f"Failed to search {url}: {e}")

    return {"jobs": all_jobs, "current_job_index": 0, "errors": errors}
```

## Alternatives Considered

- **Per-site credentials in config** — fragile, can't handle 2FA or OAuth (rejected)
- **Site-specific scrapers only** — more accurate but requires per-site maintenance (deferred to [017](017-job-site-adapters.md))
- **Job board APIs** — most are paid or restricted; browser scraping covers all sites
- **Skip pagination** — misses jobs; users expect thorough search

## Acceptance Criteria

- [ ] Node visits each URL and returns `JobListing` objects
- [ ] Login walls detected — user prompted to log in manually
- [ ] Sessions saved after login — reused on next run
- [ ] Pagination followed until no more pages
- [ ] Works with at least 2 different job site layouts
- [ ] One failing URL doesn't crash the pipeline — error is recorded, others continue
- [ ] Empty page text produces empty job list (no crash)
- [ ] Tests pass with mocked Playwright page and LLM response
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/search_jobs.py` — implement
- `src/apply_operator/prompts/job_matching.py` — add `EXTRACT_JOBS` prompt
- `src/apply_operator/tools/browser.py` — add `detect_login_required()` if not in 005
- `tests/test_search_jobs.py` — create

## Related Issues

- Blocked by [005](005-playwright-browser-basics.md)
- Blocks [008](008-minimal-graph-integration.md)
