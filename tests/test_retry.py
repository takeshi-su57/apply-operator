"""Tests for retry decorator and error classification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apply_operator.tools.retry import (
    CaptchaBlockError,
    FatalConfigError,
    LLMInvalidJSONError,
    LLMRateLimitError,
    NonRetryableError,
    PageTimeoutError,
    RetryableError,
    is_auth_error,
    is_rate_limit,
    with_retry,
)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_retryable_error_is_exception(self) -> None:
        assert issubclass(RetryableError, Exception)

    def test_page_timeout_is_retryable(self) -> None:
        assert issubclass(PageTimeoutError, RetryableError)
        assert PageTimeoutError.max_retries == 3

    def test_llm_rate_limit_is_retryable(self) -> None:
        assert issubclass(LLMRateLimitError, RetryableError)
        assert LLMRateLimitError.max_retries == 3

    def test_llm_invalid_json_is_retryable(self) -> None:
        assert issubclass(LLMInvalidJSONError, RetryableError)
        assert LLMInvalidJSONError.max_retries == 1
        assert LLMInvalidJSONError.use_backoff is False

    def test_non_retryable_error_is_exception(self) -> None:
        assert issubclass(NonRetryableError, Exception)

    def test_captcha_block_is_non_retryable(self) -> None:
        assert issubclass(CaptchaBlockError, NonRetryableError)

    def test_fatal_config_is_non_retryable(self) -> None:
        assert issubclass(FatalConfigError, NonRetryableError)


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


class TestIsRateLimit:
    def test_detects_429_status_code(self) -> None:
        exc = Exception("too many requests")
        exc.status_code = 429  # type: ignore[attr-defined]
        assert is_rate_limit(exc) is True

    def test_detects_429_in_string(self) -> None:
        exc = Exception("Error 429: rate limit exceeded")
        assert is_rate_limit(exc) is True

    def test_detects_rate_limit_text(self) -> None:
        exc = Exception("Rate limit reached for model")
        assert is_rate_limit(exc) is True

    def test_returns_false_for_other_errors(self) -> None:
        exc = Exception("Connection reset")
        assert is_rate_limit(exc) is False

    def test_detects_code_attribute(self) -> None:
        exc = Exception("limit")
        exc.code = 429  # type: ignore[attr-defined]
        assert is_rate_limit(exc) is True


class TestIsAuthError:
    def test_detects_401_status_code(self) -> None:
        exc = Exception("unauthorized")
        exc.status_code = 401  # type: ignore[attr-defined]
        assert is_auth_error(exc) is True

    def test_detects_403_status_code(self) -> None:
        exc = Exception("forbidden")
        exc.status_code = 403  # type: ignore[attr-defined]
        assert is_auth_error(exc) is True

    def test_detects_auth_in_class_name(self) -> None:
        class AuthenticationError(Exception):
            pass

        exc = AuthenticationError("invalid key")
        assert is_auth_error(exc) is True

    def test_returns_false_for_other_errors(self) -> None:
        exc = Exception("Connection error")
        assert is_auth_error(exc) is False


# ---------------------------------------------------------------------------
# Sync retry decorator
# ---------------------------------------------------------------------------


class TestWithRetrySync:
    @patch("apply_operator.tools.retry.time.sleep")
    def test_no_retry_on_success(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0)
        def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch("apply_operator.tools.retry.time.sleep")
    def test_retries_on_retryable_error(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0)
        def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise PageTimeoutError("timeout")
            return "ok"

        result = fail_twice()
        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("apply_operator.tools.retry.time.sleep")
    def test_respects_max_retries_from_exception(self, mock_sleep: MagicMock) -> None:
        """LLMInvalidJSONError has max_retries=1, so only 2 total attempts."""
        call_count = 0

        @with_retry(max_retries=5, base_delay=0.1)
        def always_bad_json() -> str:
            nonlocal call_count
            call_count += 1
            raise LLMInvalidJSONError("bad json")

        with pytest.raises(LLMInvalidJSONError):
            always_bad_json()

        # 1 initial + 1 retry = 2 total attempts
        assert call_count == 2
        assert mock_sleep.call_count == 1

    @patch("apply_operator.tools.retry.time.sleep")
    def test_non_retryable_passes_through(self, mock_sleep: MagicMock) -> None:
        @with_retry(max_retries=3, base_delay=1.0)
        def fatal() -> str:
            raise FatalConfigError("missing key")

        with pytest.raises(FatalConfigError, match="missing key"):
            fatal()

        mock_sleep.assert_not_called()

    @patch("apply_operator.tools.retry.time.sleep")
    def test_exhausted_retries_raises(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.1)
        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise PageTimeoutError("timeout")

        with pytest.raises(PageTimeoutError):
            always_fail()

        # 1 initial + 2 retries (but PageTimeoutError.max_retries=3, decorator max_retries=2)
        # effective = min is not applied; exception's max_retries (3) is used over decorator's (2)
        # actually: _effective_retries returns exception's max_retries=3
        # so: 1 initial + 3 retries = 4 attempts but loop range is max_retries+1 = 3
        # Let me reconsider: _max_attempts(max_retries=2) = 3, so loop runs 3 times (0,1,2)
        # attempt 0: raises, _effective_retries=3, 0 < 3 → retry
        # attempt 1: raises, 1 < 3 → retry
        # attempt 2: raises, 2 < 3 → retry → but loop ends (range(3))
        # Actually attempt 2 is the last iteration, so 2 < 3 is true, but the loop
        # ends because range(_max_attempts(2)) = range(3) = [0,1,2].
        # After attempt 2, the for loop ends and we hit the final raise.
        # Wait — the except block checks `if attempt >= effective_max` → 2 >= 3 is False
        # so it sleeps and continues, but the loop has no more iterations.
        # The last_exc path at the bottom handles this.
        assert call_count == 3

    @patch("apply_operator.tools.retry.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep: MagicMock) -> None:
        """Verify delays increase exponentially (with jitter in [0, delay])."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0, max_delay=60.0)
        def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise PageTimeoutError("timeout")
            return "ok"

        # Patch random.uniform to return deterministic values
        with patch("apply_operator.tools.retry.random.uniform", side_effect=lambda a, b: b):
            result = fail_then_succeed()

        assert result == "ok"
        # Delays: 1.0 * 2^0 = 1.0, 1.0 * 2^1 = 2.0, 1.0 * 2^2 = 4.0
        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]

    @patch("apply_operator.tools.retry.time.sleep")
    def test_unrelated_exception_not_retried(self, mock_sleep: MagicMock) -> None:
        @with_retry(max_retries=3, base_delay=1.0)
        def raise_value_error() -> str:
            raise ValueError("unrelated")

        with pytest.raises(ValueError, match="unrelated"):
            raise_value_error()

        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Async retry decorator
# ---------------------------------------------------------------------------


class TestWithRetryAsync:
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self) -> None:
        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0)
        async def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        with patch("apply_operator.tools.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await succeed()

        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self) -> None:
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        async def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise PageTimeoutError("timeout")
            return "ok"

        mock_sleep = AsyncMock()
        with patch("apply_operator.tools.retry.asyncio.sleep", mock_sleep):
            result = await fail_twice()

        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_passes_through(self) -> None:
        @with_retry(max_retries=3, base_delay=1.0)
        async def fatal() -> str:
            raise CaptchaBlockError("captcha found")

        with (
            pytest.raises(CaptchaBlockError, match="captcha found"),
            patch("apply_operator.tools.retry.asyncio.sleep", new_callable=AsyncMock),
        ):
            await fatal()

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise LLMRateLimitError("429")

        with (
            pytest.raises(LLMRateLimitError),
            patch("apply_operator.tools.retry.asyncio.sleep", new_callable=AsyncMock),
        ):
            await always_fail()

        # LLMRateLimitError.max_retries=3, loop range = max_retries+1 = 4
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_respects_exception_max_retries(self) -> None:
        call_count = 0

        @with_retry(max_retries=5, base_delay=0.1)
        async def bad_json() -> str:
            nonlocal call_count
            call_count += 1
            raise LLMInvalidJSONError("bad")

        with (
            pytest.raises(LLMInvalidJSONError),
            patch("apply_operator.tools.retry.asyncio.sleep", new_callable=AsyncMock),
        ):
            await bad_json()

        # max_retries from exception = 1, so 2 total attempts
        assert call_count == 2


# ---------------------------------------------------------------------------
# navigate_with_retry (browser integration)
# ---------------------------------------------------------------------------


class TestNavigateWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        from apply_operator.tools.browser import navigate_with_retry

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=None)

        with patch("apply_operator.tools.browser.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(browser_timeout=30000)
            await navigate_with_retry(mock_page, "https://example.com")

        mock_page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_playwright_timeout(self) -> None:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        from apply_operator.tools.browser import navigate_with_retry

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(
            side_effect=[PlaywrightTimeout("timeout"), PlaywrightTimeout("timeout"), None]
        )

        with (
            patch("apply_operator.tools.browser.get_settings") as mock_settings,
            patch("apply_operator.tools.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.return_value = MagicMock(browser_timeout=30000)
            await navigate_with_retry(mock_page, "https://example.com")

        assert mock_page.goto.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_page_timeout_after_exhausted_retries(self) -> None:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        from apply_operator.tools.browser import navigate_with_retry

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("timeout"))

        with (
            patch("apply_operator.tools.browser.get_settings") as mock_settings,
            patch("apply_operator.tools.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.return_value = MagicMock(browser_timeout=30000)
            with pytest.raises(PageTimeoutError, match="timed out after 3 retries"):
                await navigate_with_retry(mock_page, "https://example.com")

        # 1 initial + 3 retries = 4
        assert mock_page.goto.call_count == 4
