"""Retry decorator and error classification for transient failures."""

import asyncio
import functools
import inspect
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class RetryableError(Exception):
    """Base class for errors that should be retried."""

    max_retries: int = 3
    use_backoff: bool = True


class PageTimeoutError(RetryableError):
    """Browser page navigation or load timed out."""

    max_retries: int = 3


class LLMRateLimitError(RetryableError):
    """LLM provider returned a rate-limit (429) response."""

    max_retries: int = 3


class LLMInvalidJSONError(RetryableError):
    """LLM returned a response that could not be parsed as JSON."""

    max_retries: int = 1
    use_backoff: bool = False


class NonRetryableError(Exception):
    """Base class for errors that should NOT be retried."""


class CaptchaBlockError(NonRetryableError):
    """CAPTCHA detected in headless mode — cannot proceed."""


class FatalConfigError(NonRetryableError):
    """Fatal configuration error (missing API key, invalid credentials)."""


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def is_rate_limit(exc: Exception) -> bool:
    """Check if an exception represents a rate-limit (429) error.

    Works with openai, anthropic, and google provider exceptions by
    inspecting ``status_code`` / ``code`` attributes and string content.
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status == 429:
        return True
    exc_str = str(exc).lower()
    return "429" in exc_str or "rate limit" in exc_str


def is_auth_error(exc: Exception) -> bool:
    """Check if an exception represents an authentication error (401/403)."""
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return True
    return "auth" in type(exc).__name__.lower()


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def with_retry(
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[F], F]:
    """Decorator that retries a function on transient failures.

    Supports both sync and async callables.  If the caught exception is a
    :class:`RetryableError` subclass its ``max_retries`` attribute overrides
    the decorator-level *max_retries* parameter.

    Args:
        max_retries: Default maximum number of retries.
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Upper-bound on the back-off delay.
        retryable_exceptions: Tuple of exception types considered retryable.
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Exception | None = None
                for attempt in range(_max_attempts(max_retries)):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        if not isinstance(exc, retryable_exceptions):
                            raise
                        effective_max = _effective_retries(exc, max_retries)
                        if attempt >= effective_max:
                            raise
                        last_exc = exc
                        delay = _backoff_delay(exc, attempt, base_delay, max_delay)
                        logger.warning(
                            "Retry %d/%d for %s | %s: %s | wait %.1fs",
                            attempt + 1,
                            effective_max,
                            func.__name__,
                            type(exc).__name__,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                # Should not reach here, but satisfy the type checker.
                if last_exc is not None:  # pragma: no cover
                    raise last_exc

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(_max_attempts(max_retries)):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if not isinstance(exc, retryable_exceptions):
                        raise
                    effective_max = _effective_retries(exc, max_retries)
                    if attempt >= effective_max:
                        raise
                    last_exc = exc
                    delay = _backoff_delay(exc, attempt, base_delay, max_delay)
                    logger.warning(
                        "Retry %d/%d for %s | %s: %s | wait %.1fs",
                        attempt + 1,
                        effective_max,
                        func.__name__,
                        type(exc).__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            # Should not reach here, but satisfy the type checker.
            if last_exc is not None:  # pragma: no cover
                raise last_exc

        return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _max_attempts(max_retries: int) -> int:
    """Total attempts = initial try + retries."""
    return max_retries + 1


def _effective_retries(exc: Exception, default: int) -> int:
    """Read ``max_retries`` from the exception class, or fall back to *default*."""
    if isinstance(exc, RetryableError):
        return type(exc).max_retries
    return default


def _backoff_delay(
    exc: Exception,
    attempt: int,
    base_delay: float,
    max_delay: float,
) -> float:
    """Compute delay with exponential back-off and jitter."""
    use_backoff = True
    if isinstance(exc, RetryableError):
        use_backoff = type(exc).use_backoff

    delay = min(base_delay * (2**attempt), max_delay) if use_backoff else base_delay

    # Add jitter: uniform random between 0 and computed delay.
    return random.uniform(0, delay)
