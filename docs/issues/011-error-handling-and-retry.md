# [Feature]: Add error handling and retry logic

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [009](009-fill-application-node.md)

## Description

Add robust error handling and retry logic across the pipeline. Transient failures (network timeouts, LLM rate limits) should be retried automatically. Permanent failures (CAPTCHA, invalid credentials) should be skipped gracefully.

## Motivation

- Real-world job sites are unreliable: slow pages, rate-limited APIs, CAPTCHAs
- Without retry, a single timeout kills the pipeline for all remaining jobs
- Users expect the agent to be resilient — not crash because one site was slow

## Proposed Solution

### Retry decorator with exponential backoff

```python
def with_retry(max_attempts=3, delay=2.0, backoff=2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay * (backoff ** attempt))
        return wrapper
    return decorator
```

### Error categories

| Error | Action | Retry? |
|-------|--------|--------|
| Page timeout | Retry 3x, then skip | Yes |
| LLM rate limit (429) | Retry with backoff | Yes |
| LLM invalid JSON | Retry once with clarified prompt | Yes (1x) |
| Form field not found | Skip field, log warning | No |
| CAPTCHA detected | Skip job, warn user | No |
| File not found / API key invalid | Fail immediately | No |

### Timeout configuration

Add `PAGE_TIMEOUT` and `LLM_TIMEOUT` to `config.py` and `.env.example`.

## Alternatives Considered

- **tenacity library** — popular retry library, but a simple decorator covers our needs
- **No retry, just skip** — acceptable for v1, but retry improves success rate significantly

## Acceptance Criteria

- [ ] Transient failures retried automatically (up to 3 attempts)
- [ ] One failing job doesn't crash the pipeline — continues to next
- [ ] CAPTCHA detection warns the user and skips
- [ ] Error details recorded in `state.errors` and `data/results.json`
- [ ] Timeout values configurable via env vars
- [ ] Tests cover retry logic and error isolation
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/retry.py` — create
- `src/apply_operator/tools/browser.py` — add retry to navigation
- `src/apply_operator/tools/llm_provider.py` — add retry to LLM calls
- `src/apply_operator/nodes/fill_application.py` — error isolation
- `src/apply_operator/nodes/search_jobs.py` — error isolation
- `src/apply_operator/config.py` — add timeout settings
- `.env.example` — add timeout variables
- `tests/test_retry.py` — create

## Related Issues

- Blocked by [009](009-fill-application-node.md)
