"""Tests for SettingsManager service."""

import json

# ===================== Init / Load / Save =====================


class TestSettingsManagerInit:
    def test_creates_default_settings_when_no_file(self, tmp_path):
        from services.settings_manager import SettingsManager

        sm = SettingsManager(settings_file=tmp_path / "settings.json")
        assert sm.settings.default_provider == "gemini"
        assert (tmp_path / "settings.json").exists()

    def test_loads_existing_settings(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"gemini_api_key": "abc123", "default_provider": "claude"}))
        from services.settings_manager import SettingsManager

        sm = SettingsManager(settings_file=path)
        assert sm.settings.gemini_api_key == "abc123"
        assert sm.settings.default_provider == "claude"

    def test_falls_back_to_defaults_on_corrupt_file(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("not valid json!!!")
        from services.settings_manager import SettingsManager

        sm = SettingsManager(settings_file=path)
        assert sm.settings.default_provider == "gemini"

    def test_falls_back_on_invalid_field_values(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"unknown_field_xyz": 42}))
        from services.settings_manager import SettingsManager

        sm = SettingsManager(settings_file=path)
        assert sm.settings.default_provider == "gemini"

    def test_persists_on_first_creation(self, tmp_path):
        path = tmp_path / "settings.json"
        assert not path.exists()
        from services.settings_manager import SettingsManager

        SettingsManager(settings_file=path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["default_provider"] == "gemini"


# ===================== get_all / masking =====================


class TestGetAll:
    def test_get_all_masks_api_keys(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"gemini_api_key": "abcdefghijklmnop"})
        result = sm.get_all(mask_api_key=True)
        assert result["gemini_api_key"] == "abcd...mnop"

    def test_get_all_masks_short_keys(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"gemini_api_key": "short"})
        result = sm.get_all(mask_api_key=True)
        assert result["gemini_api_key"] == "****"

    def test_get_all_no_masking(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"gemini_api_key": "abcdefghijklmnop"})
        result = sm.get_all(mask_api_key=False)
        assert result["gemini_api_key"] == "abcdefghijklmnop"

    def test_get_all_masks_empty_key(self, settings_manager_isolated):
        sm = settings_manager_isolated
        result = sm.get_all(mask_api_key=True)
        assert result["gemini_api_key"] == ""

    def test_get_all_masks_all_key_fields(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update(
            {
                "gemini_api_key": "1234567890123456",
                "claude_api_key": "abcdefghijklmnop",
                "openai_compat_api_key": "aaaa1111bbbb2222",
                "claude_proxy_api_key": "xxxx9999yyyy8888",
            }
        )
        result = sm.get_all(mask_api_key=True)
        for field in ("gemini_api_key", "claude_api_key", "openai_compat_api_key", "claude_proxy_api_key"):
            assert "..." in result[field]

    def test_get_all_returns_all_fields(self, settings_manager_isolated):
        result = settings_manager_isolated.get_all()
        assert "default_provider" in result
        assert "gemini_model" in result
        assert "enforce_resume_one_page" in result


# ===================== update =====================


class TestUpdate:
    def test_update_single_field(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"default_provider": "claude"})
        assert sm.settings.default_provider == "claude"

    def test_update_multiple_fields(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"default_provider": "claude", "max_latex_retries": 5})
        assert sm.settings.default_provider == "claude"
        assert sm.settings.max_latex_retries == 5

    def test_update_skips_masked_api_key(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"gemini_api_key": "real_key_1234567890"})
        assert sm.settings.gemini_api_key == "real_key_1234567890"
        # Now simulate UI sending back a masked value
        sm.update({"gemini_api_key": "real...7890"})
        assert sm.settings.gemini_api_key == "real_key_1234567890"

    def test_update_ignores_unknown_keys(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"nonexistent_field": "value"})
        assert not hasattr(sm.settings, "nonexistent_field")

    def test_update_persists_to_file(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update({"max_latex_retries": 7})
        data = json.loads(path.read_text())
        assert data["max_latex_retries"] == 7

    def test_update_returns_settings(self, settings_manager_isolated):
        result = settings_manager_isolated.update({"default_provider": "claude"})
        assert result.default_provider == "claude"


# ===================== get =====================


class TestGet:
    def test_get_existing_setting(self, settings_manager_isolated):
        assert settings_manager_isolated.get("default_provider") == "gemini"

    def test_get_nonexistent_setting_returns_default(self, settings_manager_isolated):
        assert settings_manager_isolated.get("nonexistent", "fallback") == "fallback"

    def test_get_none_for_optional_field(self, settings_manager_isolated):
        assert settings_manager_isolated.get("gemini_temperature") is None


# ===================== reset_to_defaults =====================


class TestResetToDefaults:
    def test_reset_preserves_gemini_api_key(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"gemini_api_key": "my_key_12345", "max_latex_retries": 10})
        sm.reset_to_defaults()
        assert sm.settings.gemini_api_key == "my_key_12345"
        assert sm.settings.max_latex_retries == 3

    def test_reset_restores_defaults(self, settings_manager_isolated):
        sm = settings_manager_isolated
        sm.update({"default_provider": "claude", "enforce_resume_one_page": False})
        sm.reset_to_defaults()
        assert sm.settings.default_provider == "gemini"
        assert sm.settings.enforce_resume_one_page is True


# ===================== Singleton =====================


class TestSingleton:
    def test_get_settings_manager_returns_singleton(self):
        import services.settings_manager as sm_module
        from services.settings_manager import get_settings_manager

        # Reset global
        sm_module._settings_manager = None
        sm1 = get_settings_manager()
        sm2 = get_settings_manager()
        assert sm1 is sm2
        # Cleanup
        sm_module._settings_manager = None
