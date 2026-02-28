"""Tests for AI client classes (properties, init, error paths)."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ===================== GeminiClient =====================

class TestGeminiClient:
    def test_provider_name(self):
        with patch("services.gemini_client.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            from services.gemini_client import GeminiClient
            client = GeminiClient()
            assert client.provider_name == "gemini"

    def test_model_from_settings(self):
        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, *a: {
            "gemini_model": "gemini-3-pro-preview",
        }.get(key)
        with patch("services.gemini_client.get_settings_manager", return_value=mock_sm):
            from services.gemini_client import GeminiClient
            client = GeminiClient()
            assert client.model == "gemini-3-pro-preview"

    def test_get_client_raises_without_api_key(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = ""
        with patch("services.gemini_client.get_settings_manager", return_value=mock_sm), \
             patch("services.gemini_client.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            from services.gemini_client import GeminiClient
            client = GeminiClient()
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                client._get_client()

    def test_default_thinking_level(self):
        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, *a: {
            "gemini_thinking_level": None,
        }.get(key)
        with patch("services.gemini_client.get_settings_manager", return_value=mock_sm):
            from services.gemini_client import GeminiClient
            client = GeminiClient()
            assert client.default_thinking_level == "high"


# ===================== ClaudeClient =====================

class TestClaudeClient:
    def test_provider_name(self):
        with patch("services.claude_client.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            from services.claude_client import ClaudeClient
            client = ClaudeClient()
            assert client.provider_name == "claude"

    def test_model_from_settings(self):
        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, *a: {
            "claude_model": "claude-opus-4-6",
        }.get(key)
        with patch("services.claude_client.get_settings_manager", return_value=mock_sm):
            from services.claude_client import ClaudeClient
            client = ClaudeClient()
            assert client.model == "claude-opus-4-6"

    def test_model_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = None
        with patch("services.claude_client.get_settings_manager", return_value=mock_sm):
            from services.claude_client import ClaudeClient
            client = ClaudeClient()
            assert "claude" in client.model.lower()

    def test_get_client_raises_without_api_key(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = ""
        with patch("services.claude_client.get_settings_manager", return_value=mock_sm), \
             patch("services.claude_client.app_settings") as mock_settings:
            mock_settings.claude_api_key = ""
            # mock anthropic not installed
            from services.claude_client import ClaudeClient
            client = ClaudeClient()
            with pytest.raises((ValueError, ImportError)):
                client._get_client()

    def test_extended_thinking_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = False
        with patch("services.claude_client.get_settings_manager", return_value=mock_sm):
            from services.claude_client import ClaudeClient
            client = ClaudeClient()
            assert client._extended_thinking is False


# ===================== OpenAICompatClient =====================

class TestOpenAICompatClient:
    def test_provider_name(self):
        with patch("services.openai_compat_client.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            from services.openai_compat_client import OpenAICompatClient
            client = OpenAICompatClient()
            assert client.provider_name == "openai_compat"

    def test_model_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = None
        with patch("services.openai_compat_client.get_settings_manager", return_value=mock_sm), \
             patch("services.openai_compat_client.app_settings") as mock_settings:
            mock_settings.openai_compat_model = ""
            from services.openai_compat_client import OpenAICompatClient
            client = OpenAICompatClient()
            assert client.model == "gpt-4o"

    def test_temperature_property(self):
        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, *a: {
            "openai_compat_temperature": 0.7,
        }.get(key)
        with patch("services.openai_compat_client.get_settings_manager", return_value=mock_sm):
            from services.openai_compat_client import OpenAICompatClient
            client = OpenAICompatClient()
            assert client._temperature == 0.7


# ===================== ClaudeProxyClient =====================

class TestClaudeProxyClient:
    def test_provider_name(self):
        with patch("services.claude_proxy_client.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            from services.claude_proxy_client import ClaudeProxyClient
            client = ClaudeProxyClient()
            assert client.provider_name == "claude_proxy"

    def test_model_from_settings(self):
        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, *a: {
            "claude_proxy_model": "claude-haiku-4-5-20251001",
        }.get(key)
        with patch("services.claude_proxy_client.get_settings_manager", return_value=mock_sm):
            from services.claude_proxy_client import ClaudeProxyClient
            client = ClaudeProxyClient()
            assert client.model == "claude-haiku-4-5-20251001"

    def test_model_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = None
        with patch("services.claude_proxy_client.get_settings_manager", return_value=mock_sm):
            from services.claude_proxy_client import ClaudeProxyClient
            client = ClaudeProxyClient()
            assert "claude" in client.model.lower()

    def test_max_output_tokens_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = None
        with patch("services.claude_proxy_client.get_settings_manager", return_value=mock_sm):
            from services.claude_proxy_client import ClaudeProxyClient
            client = ClaudeProxyClient()
            assert client._max_output_tokens == 16384
