"""Tests for application configuration."""

from unittest.mock import patch

import pytest

from apply_operator.config import Settings, get_settings


@pytest.fixture
def _clean_env() -> None:  # type: ignore[return]
    """Clear LLM/config env vars so .env file doesn't interfere."""
    env_overrides = {
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4o",
        "LLM_MAX_TOKENS": "8192",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
        "BROWSER_HEADLESS": "true",
        "BROWSER_TIMEOUT": "30000",
        "LLM_TIMEOUT": "120000",
        "LLM_MAX_RETRIES": "3",
        "RETRY_BASE_DELAY": "1.0",
        "LOG_LEVEL": "INFO",
        "CHECKPOINT_DB": "data/checkpoints.sqlite",
    }
    with patch.dict("os.environ", env_overrides):
        yield


@pytest.mark.usefixtures("_clean_env")
class TestSettings:
    """Tests for Settings model defaults and env var loading."""

    def test_default_provider_is_openai(self) -> None:
        settings = Settings()
        assert settings.llm_provider == "openai"

    def test_default_model(self) -> None:
        settings = Settings()
        assert settings.llm_model == "gpt-4o"

    def test_default_max_tokens(self) -> None:
        settings = Settings()
        assert settings.llm_max_tokens == 8192

    def test_default_browser_headless(self) -> None:
        settings = Settings()
        assert settings.browser_headless is True

    def test_default_browser_timeout(self) -> None:
        settings = Settings()
        assert settings.browser_timeout == 30000

    def test_default_retry_settings(self) -> None:
        settings = Settings()
        assert settings.llm_timeout == 120000
        assert settings.llm_max_retries == 3
        assert settings.retry_base_delay == 1.0

    def test_default_log_level(self) -> None:
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_default_checkpoint_db(self) -> None:
        settings = Settings()
        assert settings.checkpoint_db == "data/checkpoints.sqlite"

    def test_default_api_keys_empty(self) -> None:
        settings = Settings()
        assert settings.openai_api_key == ""
        assert settings.anthropic_api_key == ""
        assert settings.google_api_key == ""
        assert settings.openrouter_api_key == ""


class TestEnvVarOverride:
    """Tests that env vars override defaults."""

    @patch.dict("os.environ", {"LLM_PROVIDER": "anthropic"})
    def test_override_provider(self) -> None:
        settings = Settings()
        assert settings.llm_provider == "anthropic"

    @patch.dict("os.environ", {"LLM_MODEL": "claude-3-opus"})
    def test_override_model(self) -> None:
        settings = Settings()
        assert settings.llm_model == "claude-3-opus"

    @patch.dict("os.environ", {"BROWSER_HEADLESS": "false"})
    def test_override_headless(self) -> None:
        settings = Settings()
        assert settings.browser_headless is False

    @patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"})
    def test_override_log_level(self) -> None:
        settings = Settings()
        assert settings.log_level == "DEBUG"

    @patch.dict("os.environ", {"CHECKPOINT_DB": "/tmp/custom.db"})
    def test_override_checkpoint_db(self) -> None:
        settings = Settings()
        assert settings.checkpoint_db == "/tmp/custom.db"


class TestGetSettings:
    """Tests for the get_settings factory."""

    def test_returns_settings_instance(self) -> None:
        result = get_settings()
        assert isinstance(result, Settings)
