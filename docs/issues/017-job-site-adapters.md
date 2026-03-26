# [Feature]: Add job site adapters for LinkedIn, Indeed, etc.

**Labels:** `enhancement`, `priority:low`
**Depends on:** [009](009-fill-application-node.md)

## Description

Add specialized adapters for popular job sites that handle site-specific quirks: custom UI components, multi-step application flows (e.g., LinkedIn Easy Apply), and non-standard page structures. Adapters improve reliability for common platforms while the generic LLM approach remains the fallback.

## Motivation

- The generic LLM-assisted approach (issues 006, 009) works for simple sites but struggles with major platforms
- LinkedIn, Indeed, and Glassdoor have custom UI components and API-loaded content
- Site-specific adapters improve reliability for the most common job sites
- All authentication is handled by the shared session system (issue 005) — adapters don't manage credentials

## Proposed Solution

### Adapter pattern

```python
# tools/adapters/base.py
class JobSiteAdapter:
    domain: str
    async def search_jobs(self, page) -> list[JobListing]: ...
    async def fill_application(self, page, resume, job) -> bool: ...
    async def find_next_page(self, page) -> bool: ...
```

**Note:** No `login()` method — authentication is handled by the shared session persistence and user intervention system from issue 005. Adapters assume the user is already logged in.

### Adapter registry

Nodes check for an adapter first, fall back to generic LLM-assisted approach:
```python
adapter = get_adapter(url)
if adapter:
    jobs = await adapter.search_jobs(page)
else:
    jobs = await generic_llm_search(page)
```

### No per-site credentials

All authentication goes through the shared flow:
1. Agent visits site → detects login wall → prompts user
2. User logs in manually → session saved to `data/sessions/<domain>.json`
3. Adapters operate on the already-authenticated page

Adapters only handle site-specific **navigation and extraction** — not authentication.

## Alternatives Considered

- **Generic-only approach** — simpler but unreliable for major sites with custom UIs
- **Per-site credentials in config** — rejected; shared session system handles all auth
- **Job board APIs** — most are paid or restricted; browser automation covers all sites

## Acceptance Criteria

- [ ] Adapter base class and registry created
- [ ] LinkedIn adapter works for Easy Apply flow (assumes user already logged in)
- [ ] Indeed adapter works for multi-step applications (assumes user already logged in)
- [ ] Unknown sites fall back to generic LLM approach
- [ ] No credentials stored in config or env vars — auth uses shared session system
- [ ] Tests pass for each adapter with mocked Playwright
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/adapters/` — create directory
  - `base.py` — base class
  - `__init__.py` — registry
  - `linkedin.py` — LinkedIn adapter
  - `indeed.py` — Indeed adapter
- `src/apply_operator/nodes/search_jobs.py` — use adapter if available
- `src/apply_operator/nodes/fill_application.py` — use adapter if available
- `tests/test_adapters/` — create

## Related Issues

- Blocked by [009](009-fill-application-node.md)
- Uses session system from [005](005-playwright-browser-basics.md)
