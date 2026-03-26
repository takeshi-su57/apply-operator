# [Feature]: Implement search_jobs node with LLM-assisted scraping

**Labels:** `enhancement`, `priority:high`
**Depends on:** [005](005-playwright-browser-basics.md)

## Description

Implement the `search_jobs` node that navigates to each job site URL provided by the user and extracts job listings using Playwright for page loading and LLM for content extraction.

## Motivation

- Users provide raw URLs (job search pages, company career pages) — the agent needs to understand arbitrary page layouts
- Hardcoded CSS selectors per site are fragile; LLM-assisted extraction adapts to any layout
- This node populates the `jobs` list that all downstream nodes consume

## Proposed Solution

**LLM-assisted scraping approach:**
1. Load page with Playwright, wait for content
2. Extract visible text (truncated to ~8000 chars for LLM context)
3. Send text to LLM with `EXTRACT_JOBS` prompt
4. Parse JSON response into `JobListing` objects
5. Handle errors per URL — one failing site doesn't crash the pipeline

### New prompt needed

Add `EXTRACT_JOBS` to `prompts/job_matching.py`:
- Input: page text + source URL
- Output: JSON array of `{title, company, description, location, apply_url}`

### Async node pattern

```python
async def search_jobs(state: ApplicationState) -> dict:
    all_jobs, errors = [], list(state.errors)
    for url in state.job_urls:
        try:
            async with get_page() as page:
                await page.goto(url, timeout=30000)
                text = await get_page_text(page)
            listings = json.loads(call_llm(EXTRACT_JOBS.format(page_text=text[:8000], url=url)))
            all_jobs.extend(JobListing(url=item.get("apply_url", url), **item) for item in listings)
        except Exception as e:
            errors.append(f"Failed to search {url}: {e}")
    return {"jobs": all_jobs, "current_job_index": 0, "errors": errors}
```

## Alternatives Considered

- **Site-specific scrapers** — more accurate but requires per-site maintenance (deferred to [017](017-job-site-adapters.md))
- **Job board APIs** — most are paid or restricted; browser scraping covers all sites

## Acceptance Criteria

- [ ] Node visits each URL and returns `JobListing` objects
- [ ] Works with at least 2 different job site layouts
- [ ] One failing URL doesn't crash the pipeline — error is recorded, others continue
- [ ] Empty page text produces empty job list (no crash)
- [ ] Tests pass with mocked Playwright page and LLM response
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/search_jobs.py` — implement
- `src/apply_operator/prompts/job_matching.py` — add `EXTRACT_JOBS` prompt
- `src/apply_operator/tools/browser.py` — add `get_page_text()` if not done in 005
- `tests/test_search_jobs.py` — create

## Related Issues

- Blocked by [005](005-playwright-browser-basics.md)
- Blocks [008](008-minimal-graph-integration.md)
