# [Feature]: Add job site adapters for LinkedIn, Indeed, etc.

**Labels:** `enhancement`, `priority:low`
**Depends on:** [009](009-fill-application-node.md)

## Description

Add specialized adapters for popular job sites that handle site-specific quirks: login requirements, anti-bot protections, multi-step application flows, and custom form components.

## Motivation

- The generic LLM-assisted approach (issues 006, 009) works for simple sites but struggles with major platforms
- LinkedIn, Indeed, and Glassdoor have login walls, custom UI components, and API-loaded content
- Site-specific adapters improve reliability for the most common job sites

## Proposed Solution

### Adapter pattern

```python
# tools/adapters/base.py
class JobSiteAdapter:
    domain: str
    async def login(self, page, credentials): ...
    async def search_jobs(self, page, query) -> list[JobListing]: ...
    async def fill_application(self, page, resume, job) -> bool: ...

# tools/adapters/__init__.py
def get_adapter(url: str) -> JobSiteAdapter | None:
    """Return site-specific adapter, or None for generic handling."""
```

### Adapter registry

Nodes check for an adapter first, fall back to generic LLM-assisted approach:
```python
adapter = get_adapter(url)
if adapter:
    jobs = await adapter.search_jobs(page, query)
else:
    jobs = await generic_llm_search(page)
```

### Site credentials

Add to config and `.env.example`:
- `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`
- `INDEED_EMAIL`, `INDEED_PASSWORD`

## Alternatives Considered

- **Generic-only approach** — simpler but unreliable for major sites with custom UIs
- **Job board APIs** — most are paid or restricted; browser automation covers all sites
- **Browser extension** — requires user installation; CLI-only is more portable

## Acceptance Criteria

- [ ] Adapter base class and registry created
- [ ] LinkedIn adapter works for Easy Apply flow
- [ ] Indeed adapter works for multi-step applications
- [ ] Unknown sites fall back to generic LLM approach
- [ ] Site credentials stored in env vars (never hardcoded)
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
- `src/apply_operator/config.py` — add site credentials
- `.env.example` — add site credential placeholders
- `tests/test_adapters/` — create

## Related Issues

- Blocked by [009](009-fill-application-node.md)
