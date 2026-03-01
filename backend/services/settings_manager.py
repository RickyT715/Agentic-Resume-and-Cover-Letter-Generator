"""
Settings Manager Service
Handles loading, saving, and managing application settings.
Settings are persisted to a JSON file and can be modified via the UI.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AppSettings(BaseModel):
    """Application settings model."""

    # Provider Selection
    default_provider: str = "gemini"

    # Gemini API Settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-pro-preview"
    gemini_temperature: float | None = None
    gemini_top_k: int | None = None
    gemini_top_p: float | None = None
    gemini_max_output_tokens: int | None = None
    gemini_thinking_level: str = "high"
    gemini_enable_search: bool = False

    # Claude (Anthropic) Settings
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_temperature: float | None = None
    claude_max_output_tokens: int | None = None
    claude_extended_thinking: bool = False
    claude_thinking_budget: int = 10000

    # OpenAI-Compatible Proxy Settings
    openai_compat_base_url: str = "http://localhost:3000/v1"
    openai_compat_api_key: str = ""
    openai_compat_model: str = "gpt-4o"
    openai_compat_temperature: float | None = None
    openai_compat_max_output_tokens: int | None = None

    # Claude Code Proxy Settings
    claude_proxy_base_url: str = "http://localhost:42069"
    claude_proxy_api_key: str = ""
    claude_proxy_model: str = "claude-sonnet-4-5-20250929"
    claude_proxy_temperature: float | None = None
    claude_proxy_max_output_tokens: int | None = None

    # Page Length Validation
    enforce_resume_one_page: bool = True
    enforce_cover_letter_one_page: bool = True
    max_page_retry_attempts: int = 3

    # Generation Settings
    generate_cover_letter: bool = True
    max_latex_retries: int = 3
    default_template_id: str = "classic"

    # Per-Agent Provider Overrides
    # Maps agent name -> provider id. Empty string means "use task default".
    # Agents: jd_analyzer, relevance_matcher, resume_writer, cover_letter_writer, company_researcher
    agent_providers: dict[str, str] = {}


class SettingsManager:
    """Manages application settings with persistence."""

    def __init__(self, settings_file: Path = None):
        if settings_file is None:
            settings_file = Path(__file__).parent.parent / "settings.json"

        self.settings_file = settings_file
        self._settings: AppSettings | None = None
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from file or create defaults."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    data = json.load(f)
                self._settings = AppSettings(**data)
                logger.info(f"Loaded settings from {self.settings_file}")
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}. Using defaults.")
                self._settings = AppSettings()
        else:
            logger.info("No settings file found. Using defaults.")
            self._settings = AppSettings()
            self._save_settings()

    def _save_settings(self) -> None:
        """Save current settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self._settings.model_dump(), f, indent=2)
            logger.info(f"Saved settings to {self.settings_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise

    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings

    def get_all(self, mask_api_key: bool = True) -> dict[str, Any]:
        """Get all settings as a dictionary, optionally masking API keys."""
        data = self._settings.model_dump()
        if mask_api_key:
            for key_field in ("gemini_api_key", "claude_api_key", "openai_compat_api_key", "claude_proxy_api_key"):
                if data.get(key_field):
                    key = data[key_field]
                    if len(key) > 8:
                        data[key_field] = key[:4] + "..." + key[-4:]
                    else:
                        data[key_field] = "****"
        return data

    _api_key_fields = {"gemini_api_key", "claude_api_key", "openai_compat_api_key", "claude_proxy_api_key"}

    def update(self, updates: dict[str, Any]) -> AppSettings:
        """Update settings with new values."""
        current = self._settings.model_dump()

        for key, value in updates.items():
            if key in current:
                # Skip masked API key values
                if key in self._api_key_fields and value and "..." in value:
                    continue
                # For agent_providers, strip empty-string values (means "use default")
                if key == "agent_providers" and isinstance(value, dict):
                    value = {k: v for k, v in value.items() if v}
                current[key] = value
                logger.debug(f"Updated setting: {key}")

        self._settings = AppSettings(**current)
        self._save_settings()

        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        return getattr(self._settings, key, default)

    def reset_to_defaults(self) -> AppSettings:
        """Reset all settings to defaults (preserving API key)."""
        api_key = self._settings.gemini_api_key
        self._settings = AppSettings(gemini_api_key=api_key)
        self._save_settings()
        logger.info("Reset settings to defaults (preserved API key)")
        return self._settings


# Global settings manager instance
_settings_manager: SettingsManager | None = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
