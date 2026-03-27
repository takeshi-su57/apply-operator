"""Configurable LLM provider factory."""

import logging
import time

from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from apply_operator.config import get_settings

logger = logging.getLogger(__name__)


def get_llm() -> BaseChatModel:
    """Get an LLM instance based on configuration.

    Reads LLM_PROVIDER and related settings from environment.
    Supports: openai, anthropic, google, openrouter.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=settings.llm_model,
            api_key=SecretStr(settings.openai_api_key),
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=settings.llm_model,
            api_key=SecretStr(settings.anthropic_api_key),
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )

    if settings.llm_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            max_output_tokens=settings.llm_max_tokens,
        )

    if settings.llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=settings.llm_model,
            api_key=SecretStr(settings.openrouter_api_key),
            base_url=settings.openrouter_base_url,
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )

    msg = f"Unknown LLM provider: {settings.llm_provider}"
    raise ValueError(msg)


def call_llm(prompt: str, *, purpose: str = "") -> str:
    """Call the configured LLM with a prompt and return the response text.

    Convenience wrapper around get_llm() that handles AIMessage extraction.

    Args:
        prompt: The prompt to send to the LLM.
        purpose: Short description of why this call is being made (for logging).
    """
    settings = get_settings()
    llm = get_llm()

    purpose_str = f" purpose={purpose}" if purpose else ""
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

    return content
