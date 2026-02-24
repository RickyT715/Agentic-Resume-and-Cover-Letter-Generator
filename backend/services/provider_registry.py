"""
Provider registry: factory and cache for AI provider clients.
Resolves provider by name, caches instances, and handles per-task overrides.
"""
import logging
from typing import Dict, Optional, List

from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

# Cached provider instances
_providers: Dict[str, AIClientBase] = {}

AVAILABLE_PROVIDERS: List[dict] = [
    {
        "id": "gemini",
        "name": "Google Gemini",
        "description": "Google's Gemini models (recommended)",
    },
    {
        "id": "claude",
        "name": "Anthropic Claude",
        "description": "Anthropic's Claude models via API",
    },
    {
        "id": "openai_compat",
        "name": "OpenAI-Compatible Proxy",
        "description": "Any OpenAI-compatible API (Claude Code proxy, Ollama, LM Studio, etc.)",
    },
    {
        "id": "claude_proxy",
        "name": "Claude Code Proxy",
        "description": "Claude via local claude-code-proxy (Anthropic API)",
    },
]


def get_provider(name: str) -> AIClientBase:
    """
    Get a provider instance by name. Instances are cached.

    Args:
        name: Provider identifier ('gemini', 'claude', 'openai_compat')

    Returns:
        An AIClientBase instance

    Raises:
        ValueError: If the provider name is unknown
    """
    if name in _providers:
        return _providers[name]

    if name == "gemini":
        from services.gemini_client import GeminiClient

        client = GeminiClient()
    elif name == "claude":
        from services.claude_client import ClaudeClient

        client = ClaudeClient()
    elif name == "openai_compat":
        from services.openai_compat_client import OpenAICompatClient

        client = OpenAICompatClient()
    elif name == "claude_proxy":
        from services.claude_proxy_client import ClaudeProxyClient

        client = ClaudeProxyClient()
    else:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {[p['id'] for p in AVAILABLE_PROVIDERS]}"
        )

    _providers[name] = client
    logger.info(f"Created and cached provider: {name}")
    return client


def get_default_provider() -> AIClientBase:
    """Get the provider configured as the global default."""
    sm = get_settings_manager()
    default_name = sm.get("default_provider") or "gemini"
    return get_provider(default_name)


def get_provider_for_task(task_provider: Optional[str]) -> AIClientBase:
    """
    Resolve the provider for a specific task.

    Args:
        task_provider: Per-task provider override (None means use default)

    Returns:
        The resolved AIClientBase instance
    """
    if task_provider:
        return get_provider(task_provider)
    return get_default_provider()
