"""Tests for provider_registry module."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_provider_cache():
    """Clear the provider cache before each test."""
    import services.provider_registry as pr

    pr._providers.clear()
    yield
    pr._providers.clear()


class TestGetProvider:
    def test_creates_gemini_provider(self):
        with patch("services.gemini_client.GeminiClient") as MockGemini:
            MockGemini.return_value = MagicMock()
            from services.provider_registry import get_provider

            provider = get_provider("gemini")
            assert provider is not None
            MockGemini.assert_called_once()

    def test_creates_claude_provider(self):
        with patch("services.claude_client.ClaudeClient") as MockClaude:
            MockClaude.return_value = MagicMock()
            from services.provider_registry import get_provider

            provider = get_provider("claude")
            assert provider is not None
            MockClaude.assert_called_once()

    def test_creates_openai_compat_provider(self):
        with patch("services.openai_compat_client.OpenAICompatClient") as MockOAI:
            MockOAI.return_value = MagicMock()
            from services.provider_registry import get_provider

            provider = get_provider("openai_compat")
            assert provider is not None
            MockOAI.assert_called_once()

    def test_creates_claude_proxy_provider(self):
        with patch("services.claude_proxy_client.ClaudeProxyClient") as MockProxy:
            MockProxy.return_value = MagicMock()
            from services.provider_registry import get_provider

            provider = get_provider("claude_proxy")
            assert provider is not None
            MockProxy.assert_called_once()

    def test_raises_on_unknown_provider(self):
        from services.provider_registry import get_provider

        with pytest.raises(ValueError, match="Unknown provider 'banana'"):
            get_provider("banana")

    def test_caches_provider_instances(self):
        with patch("services.gemini_client.GeminiClient") as MockGemini:
            MockGemini.return_value = MagicMock()
            from services.provider_registry import get_provider

            p1 = get_provider("gemini")
            p2 = get_provider("gemini")
            assert p1 is p2
            MockGemini.assert_called_once()


class TestGetDefaultProvider:
    def test_returns_default_from_settings(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = "claude"
        with (
            patch("services.provider_registry.get_settings_manager", return_value=mock_sm),
            patch("services.claude_client.ClaudeClient", return_value=MagicMock()),
        ):
            from services.provider_registry import get_default_provider

            provider = get_default_provider()
            assert provider is not None

    def test_falls_back_to_gemini(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = None
        with (
            patch("services.provider_registry.get_settings_manager", return_value=mock_sm),
            patch("services.gemini_client.GeminiClient", return_value=MagicMock()),
        ):
            from services.provider_registry import get_default_provider

            provider = get_default_provider()
            assert provider is not None


class TestGetProviderForTask:
    def test_uses_task_override(self):
        with patch("services.claude_client.ClaudeClient", return_value=MagicMock()):
            from services.provider_registry import get_provider_for_task

            provider = get_provider_for_task("claude")
            assert provider is not None

    def test_uses_default_when_no_override(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        with (
            patch("services.provider_registry.get_settings_manager", return_value=mock_sm),
            patch("services.gemini_client.GeminiClient", return_value=MagicMock()),
        ):
            from services.provider_registry import get_provider_for_task

            provider = get_provider_for_task(None)
            assert provider is not None

    def test_empty_string_uses_default(self):
        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        with (
            patch("services.provider_registry.get_settings_manager", return_value=mock_sm),
            patch("services.gemini_client.GeminiClient", return_value=MagicMock()),
        ):
            from services.provider_registry import get_provider_for_task

            # empty string is falsy -> should use default
            provider = get_provider_for_task("")
            assert provider is not None


class TestAvailableProviders:
    def test_available_providers_list(self):
        from services.provider_registry import AVAILABLE_PROVIDERS

        ids = [p["id"] for p in AVAILABLE_PROVIDERS]
        assert "gemini" in ids
        assert "claude" in ids
        assert "openai_compat" in ids
        assert "claude_proxy" in ids
        assert len(AVAILABLE_PROVIDERS) == 4
