"""Configurable LLM provider factory."""

from langchain_core.language_models import BaseChatModel

from apply_operator.config import get_settings


def get_llm() -> BaseChatModel:
    """Get an LLM instance based on configuration.

    Reads LLM_PROVIDER and related settings from environment.
    Supports: openai, anthropic, google.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
        )

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0.3,
        )

    if settings.llm_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
        )

    msg = f"Unknown LLM provider: {settings.llm_provider}"
    raise ValueError(msg)
