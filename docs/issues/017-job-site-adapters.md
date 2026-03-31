# [Feature]: Add job site adapters for LinkedIn, Indeed, etc.

**Labels:** `enhancement`, `priority:low`
**Depends on:** [009](009-fill-application-node.md)

## Description

Add specialized adapters for popular job sites that handle site-specific quirks: custom UI components, multi-step application flows (e.g., LinkedIn Easy Apply), and non-standard page structures. Adapters improve reliability for common platforms while the generic LLM approach remains the fallback.

## Motivation

- The generic LLM-assisted approach works for simple sites but struggles with major platforms
- LinkedIn, Indeed, and Glassdoor have custom UI components and API-loaded content
- Site-specific adapters improve reliability for the most common job sites
- All authentication is handled by the shared session system -- adapters don't manage credentials

## Implementation

### Adapter pattern

`JobSiteAdapter` abstract base class in `tools/adapters/base.py`:

```python
class JobSiteAdapter(ABC):
    domain: str
    def matches(self, url: str) -> bool: ...          # URL domain check
    async def search_jobs(self, page, url) -> list[JobListing]: ...
    async def fill_application(self, page, resume, job) -> bool: ...
    async def find_next_page(self, page) -> bool: ...
```

### Adapter registry

`get_adapter(url)` in `tools/adapters/__init__.py` iterates registered adapters and returns first match or `None`. Nodes check adapter first, fall back to generic:

```python
adapter = get_adapter(url)
if adapter:
    page_jobs = await adapter.search_jobs(page, url)
else:
    page_jobs = await _extract_jobs_from_page(page, url)  # generic LLM
```

### LinkedIn adapter (`linkedin.py`)

- **search_jobs**: Extracts job cards via LinkedIn-specific selectors (`.job-card-container`, `.artdeco-entity-lockup__title`)
- **fill_application**: Handles Easy Apply modal flow -- clicks Easy Apply button, steps through modal pages with form fields, submits. Returns `False` if Easy Apply button not found (triggers generic fallback)
- **find_next_page**: LinkedIn pagination button selector
- **_resolve_field_value**: Heuristic field mapping (email/phone/name from resume)

### Indeed adapter (`indeed.py`)

- **search_jobs**: Extracts job cards via Indeed-specific selectors (`.job_seen_beacon`, `[data-testid='job-title']`)
- **fill_application**: Handles Indeed's multi-step apply flow -- clicks Apply button, fills form pages, submits. Returns `False` if Apply button not found
- **find_next_page**: Indeed pagination nav selector
- **_resolve_field_value**: Same heuristic field mapping pattern

### Node integration

- **search_jobs.py**: After page ready + login check, calls `get_adapter(url)`. If adapter exists, uses `adapter.search_jobs()` + `adapter.find_next_page()` in loop. Otherwise generic LLM extraction.
- **fill_application.py**: After CAPTCHA check, calls `get_adapter(job.url)`. If adapter succeeds, marks job applied. If adapter returns `False`, falls through to generic form filler.

### Graceful degradation

Adapters never hard-fail the pipeline:
- `search_jobs()` returning `[]` -> generic LLM extraction takes over
- `fill_application()` returning `False` -> generic form filler takes over
- Selector breakage (site redesign) -> same fallback behavior

## Alternatives Considered

- **Generic-only approach** -- simpler but unreliable for major sites with custom UIs
- **Per-site credentials in config** -- rejected; shared session system handles all auth
- **Job board APIs** -- most are paid or restricted; browser automation covers all sites

## Acceptance Criteria

- [x] Adapter base class and registry created
- [x] LinkedIn adapter works for Easy Apply flow (assumes user already logged in)
- [x] Indeed adapter works for multi-step applications (assumes user already logged in)
- [x] Unknown sites fall back to generic LLM approach
- [x] No credentials stored in config or env vars -- auth uses shared session system
- [x] Tests pass for each adapter with mocked Playwright (21 tests)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/adapters/` -- **new directory**
  - `base.py` -- `JobSiteAdapter` ABC
  - `__init__.py` -- registry + `get_adapter()`
  - `linkedin.py` -- LinkedIn adapter
  - `indeed.py` -- Indeed adapter
- `src/apply_operator/nodes/search_jobs.py` -- adapter check before generic extraction
- `src/apply_operator/nodes/fill_application.py` -- adapter check before generic form filling
- `tests/test_adapters.py` -- **new**: 21 tests

## Related Issues

- Blocked by [009](009-fill-application-node.md)
- Uses session system from [005](005-playwright-browser-basics.md)
