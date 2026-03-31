# [Feature]: Add error handling and retry logic

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [009](009-fill-application-node.md)

## Description

Add robust error handling and retry logic across the pipeline. Transient failures (network timeouts, LLM rate limits) should be retried automatically. Permanent failures (CAPTCHA, invalid credentials) should be skipped gracefully.

## Motivation

- Real-world job sites are unreliable: slow pages, rate-limited APIs, CAPTCHAs
- Without retry, a single timeout kills the pipeline for all remaining jobs
- Users expect the agent to be resilient — not crash because one site was slow

## Implementation

### Exception hierarchy (`src/apply_operator/tools/retry.py`)

Custom exception classes that carry retry policy as class attributes:

| Exception | Parent | `max_retries` | `use_backoff` |
|-----------|--------|---------------|---------------|
| `RetryableError` | `Exception` | 3 | True |
| `PageTimeoutError` | `RetryableError` | 3 | True |
| `LLMRateLimitError` | `RetryableError` | 3 | True |
| `LLMInvalidJSONError` | `RetryableError` | 1 | False |
| `NonRetryableError` | `Exception` | — | — |
| `CaptchaBlockError` | `NonRetryableError` | — | — |
| `FatalConfigError` | `NonRetryableError` | — | — |

### Retry decorator (`with_retry`)

Generic decorator supporting both sync and async functions with:
- Exponential backoff: `delay = min(base_delay * 2^attempt, max_delay)` + jitter
- Reads `max_retries` from the exception class when it's a `RetryableError` subclass
- Non-retryable exceptions pass through immediately
- Logs each retry at WARNING level

### Detection helpers

- `is_rate_limit(exc)` — detects 429 via `status_code` attribute or string matching
- `is_auth_error(exc)` — detects 401/403 via `status_code` or class name

### Error categories (as implemented)

| Error | Action | Retry? |
|-------|--------|--------|
| Page timeout (Playwright `TimeoutError`) | `navigate_with_retry` retries 3x with backoff, then raises `PageTimeoutError` | Yes (3x) |
| LLM rate limit (429) | `call_llm` retries up to `LLM_MAX_RETRIES` with exponential backoff | Yes (3x) |
| LLM invalid JSON | `call_llm` with `expect_json=True` retries once | Yes (1x) |
| Form field not found | `_fill_field` catches and logs warning, continues | No |
| CAPTCHA detected (headless) | Node catches `CaptchaBlockError`, skips job, warns user | No |
| Auth error (401/403) / invalid API key | Raises `FatalConfigError` immediately, stops pipeline | No |

### LLM provider changes (`src/apply_operator/tools/llm_provider.py`)

- `get_llm()` now passes `llm_timeout` to underlying SDK clients (`request_timeout` for OpenAI/OpenRouter, `timeout` for Anthropic/Google)
- `call_llm()` gained `expect_json: bool = False` parameter:
  - Rate-limit retry with exponential backoff (up to `llm_max_retries`)
  - Auth errors converted to `FatalConfigError` (no retry)
  - When `expect_json=True`, validates response as JSON and retries once on parse failure
  - Raises `LLMInvalidJSONError` if JSON still invalid after retry

### Browser changes (`src/apply_operator/tools/browser.py`)

- New `navigate_with_retry(page, url)` function: wraps `page.goto()` with 3x retry on Playwright `TimeoutError`, raises `PageTimeoutError` after exhaustion

### Node changes

All 4 nodes updated:
- **`search_jobs`** — Uses `navigate_with_retry`, catches `PageTimeoutError`/`CaptchaBlockError` (skip URL, continue), re-raises `FatalConfigError`
- **`fill_application`** — Uses `navigate_with_retry`, `expect_json=True` for field mapping, catches `PageTimeoutError`/`CaptchaBlockError` (skip job, increment `total_skipped`), re-raises `FatalConfigError`
- **`parse_resume`** — `expect_json=True` for LLM call, re-raises `FatalConfigError`
- **`analyze_fit`** — `expect_json=True` for LLM call, re-raises `FatalConfigError`

### Configuration (`config.py` / `.env.example`)

New environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TIMEOUT` | `120000` | LLM call timeout in milliseconds |
| `LLM_MAX_RETRIES` | `3` | Max retries for LLM rate-limit errors |
| `RETRY_BASE_DELAY` | `1.0` | Base delay in seconds for exponential backoff |

## Acceptance Criteria

- [x] Transient failures retried automatically (up to 3 attempts)
- [x] One failing job doesn't crash the pipeline — continues to next
- [x] CAPTCHA detection warns the user and skips
- [x] Error details recorded in `state.errors` and `data/results.json`
- [x] Timeout values configurable via env vars
- [x] Tests cover retry logic and error isolation
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/retry.py` — **created**: exception hierarchy, `with_retry` decorator, detection helpers
- `src/apply_operator/tools/llm_provider.py` — rate-limit retry, `expect_json`, auth error detection, timeout passthrough
- `src/apply_operator/tools/browser.py` — `navigate_with_retry` function
- `src/apply_operator/nodes/search_jobs.py` — uses `navigate_with_retry`, specific error catches
- `src/apply_operator/nodes/fill_application.py` — uses `navigate_with_retry`, `expect_json=True`, specific error catches
- `src/apply_operator/nodes/parse_resume.py` — `expect_json=True`, `FatalConfigError` re-raise
- `src/apply_operator/nodes/analyze_fit.py` — `expect_json=True`, `FatalConfigError` re-raise
- `src/apply_operator/config.py` — added `llm_timeout`, `llm_max_retries`, `retry_base_delay`
- `.env.example` — added 3 new env vars
- `tests/test_retry.py` — **created**: 31 tests (hierarchy, helpers, sync/async decorator, navigate_with_retry)
- `tests/test_llm_provider.py` — 6 new tests (rate-limit retry, auth error, JSON retry)

## Related Issues

- Blocked by [009](009-fill-application-node.md)
