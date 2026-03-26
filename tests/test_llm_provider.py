"""Tests for LLM provider factory."""

from unittest.mock import MagicMock, patch

import pytest

from apply_operator.config import Settings


def _make_settings(**overrides: str) -> Settings:
    """Create a Settings instance with test defaults."""
    defaults = {
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "openai_api_key": "test-openai-key",
        "anthropic_api_key": "test-anthropic-key",
        "google_api_key": "test-google-key",
        "openrouter_api_key": "test-openrouter-key",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class TestGetLlm:
    """Tests for get_llm factory function."""

    @patch("apply_operator.tools.llm_provider.get_settings")
    @patch("langchain_openai.ChatOpenAI", autospec=True)
    def test_returns_chat_openai_for_openai_provider(
        self, mock_cls: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value = _make_settings(llm_provider="openai")
        from apply_operator.tools.llm_provider import get_llm

        result = get_llm()
        mock_cls.assert_called_once()
        assert result is mock_cls.return_value

    @patch("apply_operator.tools.llm_provider.get_settings")
    @patch("langchain_anthropic.ChatAnthropic", autospec=True)
    def test_returns_chat_anthropic_for_anthropic_provider(
        self, mock_cls: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value = _make_settings(llm_provider="anthropic")
        from apply_operator.tools.llm_provider import get_llm

        result = get_llm()
        mock_cls.assert_called_once()
        assert result is mock_cls.return_value

    @patch("apply_operator.tools.llm_provider.get_settings")
    @patch("langchain_google_genai.ChatGoogleGenerativeAI", autospec=True)
    def test_returns_chat_google_for_google_provider(
        self, mock_cls: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value = _make_settings(llm_provider="google")
        from apply_operator.tools.llm_provider import get_llm

        result = get_llm()
        mock_cls.assert_called_once()
        assert result is mock_cls.return_value

    @patch("apply_operator.tools.llm_provider.get_settings")
    @patch("langchain_openai.ChatOpenAI", autospec=True)
    def test_returns_chat_openai_for_openrouter_provider(
        self, mock_cls: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value = _make_settings(llm_provider="openrouter")
        from apply_operator.tools.llm_provider import get_llm

        result = get_llm()
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert result is mock_cls.return_value

    @patch("apply_operator.tools.llm_provider.get_settings")
    def test_raises_value_error_for_unknown_provider(
        self, mock_settings: MagicMock
    ) -> None:
        settings = _make_settings()
        object.__setattr__(settings, "llm_provider", "unknown")
        mock_settings.return_value = settings
        from apply_operator.tools.llm_provider import get_llm

        with pytest.raises(ValueError, match="Unknown LLM provider: unknown"):
            get_llm()


class TestCallLlm:
    """Tests for call_llm convenience wrapper."""

    @patch("apply_operator.tools.llm_provider.get_llm")
    def test_returns_string_content(self, mock_get_llm: MagicMock) -> None:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Hello from LLM"
        mock_get_llm.return_value = mock_llm

        from apply_operator.tools.llm_provider import call_llm

        result = call_llm("Say hello")
        assert result == "Hello from LLM"
        mock_llm.invoke.assert_called_once_with("Say hello")
