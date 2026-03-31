"""Configurable LLM provider factory with retry logic."""

import json
import logging
import time

from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from apply_operator.config import get_settings
from apply_operator.tools.retry import (
    FatalConfigError,
    LLMInvalidJSONError,
    LLMRateLimitError,
    is_auth_error,
    is_rate_limit,
)

logger = logging.getLogger(__name__)


def _strip_markdown_json(text: str) -> str:
    """Remove markdown code fences from a JSON string."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else 3
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def get_llm() -> BaseChatModel:
    """Get an LLM instance based on configuration.

    Reads LLM_PROVIDER and related settings from environment.
    Supports: openai, anthropic, google, openrouter.

    The configured ``llm_timeout`` (ms) is passed to the underlying client
    so that requests time out at the SDK level.
    """
    settings = get_settings()
    timeout_s = settings.llm_timeout / 1000

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=settings.llm_model,
            api_key=SecretStr(settings.openai_api_key),
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
            request_timeout=timeout_s,
        )

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=settings.llm_model,
            api_key=SecretStr(settings.anthropic_api_key),
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
            timeout=timeout_s,
        )

    if settings.llm_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            max_output_tokens=settings.llm_max_tokens,
            timeout=timeout_s,
        )

    if settings.llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=settings.llm_model,
            api_key=SecretStr(settings.openrouter_api_key),
            base_url=settings.openrouter_base_url,
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
            request_timeout=timeout_s,
        )

    msg = f"Unknown LLM provider: {settings.llm_provider}"
    raise ValueError(msg)


def call_llm(prompt: str, *, purpose: str = "", expect_json: bool = False) -> str:
    """Call the configured LLM with a prompt and return the response text.

    Includes automatic retry for rate-limit (429) errors and, when
    *expect_json* is ``True``, a single re-try when the response is not
    valid JSON.

    Authentication errors (401/403) are raised immediately as
    :class:`FatalConfigError`.

    Args:
        prompt: The prompt to send to the LLM.
        purpose: Short description of why this call is being made (for logging).
        expect_json: When ``True``, validate the response as JSON and retry
            once on parse failure.
    """
    settings = get_settings()
    llm = get_llm()

    purpose_str = f" purpose={purpose}" if purpose else ""
    max_retries = settings.llm_max_retries
    base_delay = settings.retry_base_delay

    content = ""
    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "LLM call | provider=%s model=%s%s",
                settings.llm_provider,
                settings.llm_model,
                purpose_str,
            )
            logger.debug("LLM prompt | %d chars", len(prompt))
            start = time.perf_counter()
            response = llm.invoke(prompt)
            elapsed = time.perf_counter() - start
            content = str(response.content)
            logger.info("LLM call | completed | %.2fs | ~%d chars", elapsed, len(content))
            break
        except Exception as exc:
            if is_auth_error(exc):
                msg = f"Authentication failed for {settings.llm_provider}: {exc}"
                raise FatalConfigError(msg) from exc
            if is_rate_limit(exc) and attempt < max_retries:
                delay = min(base_delay * (2**attempt), 60.0)
                logger.warning(
                    "LLM rate limit | attempt %d/%d | retrying in %.1fs | %s",
                    attempt + 1,
                    max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)
                continue
            if is_rate_limit(exc):
                raise LLMRateLimitError(str(exc)) from exc
            raise

    # JSON validation with one retry
    if expect_json:
        try:
            json.loads(_strip_markdown_json(content))
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM returned invalid JSON | retrying once | purpose=%s", purpose)
            try:
                start = time.perf_counter()
                response = llm.invoke(prompt)
                elapsed = time.perf_counter() - start
                content = str(response.content)
                logger.info(
                    "LLM call (JSON retry) | completed | %.2fs | ~%d chars",
                    elapsed,
                    len(content),
                )
                json.loads(_strip_markdown_json(content))
            except (json.JSONDecodeError, ValueError) as json_exc:
                raise LLMInvalidJSONError(
                    f"LLM returned invalid JSON after retry: {content[:200]}"
                ) from json_exc
            except Exception as exc:
                if is_auth_error(exc):
                    msg = f"Authentication failed for {settings.llm_provider}: {exc}"
                    raise FatalConfigError(msg) from exc
                raise

    return content
