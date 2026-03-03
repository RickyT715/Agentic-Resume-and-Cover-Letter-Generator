"""Integration tests for settings → prompt manager flow.

Verifies that changing settings (e.g., allow_ai_fabrication, enforce_one_page)
results in the prompt manager selecting the correct prompt variant.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSettingsToPromptIntegration:
    """Test that settings changes propagate to correct prompt variant selection."""

    def test_fabrication_off_selects_no_fab_resume_prompt(self, settings_manager_isolated, prompt_manager):
        """When allow_ai_fabrication=False in settings, prompt_manager should use no-fab variant."""
        sm = settings_manager_isolated
        sm.update({"allow_ai_fabrication": False})
        assert sm.settings.allow_ai_fabrication is False

        # Now use the setting to drive prompt selection
        allow_fab = sm.get("allow_ai_fabrication")
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=allow_fab
        )
        # The no-fabrication prompt has distinctive content
        assert "no-fabrication" in result.lower() or "Only use verified" in result

    def test_fabrication_on_selects_standard_resume_prompt(self, settings_manager_isolated, prompt_manager):
        """When allow_ai_fabrication=True (default), standard prompt is used."""
        sm = settings_manager_isolated
        # Default should be True
        allow_fab = sm.get("allow_ai_fabrication")
        assert allow_fab is True

        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=allow_fab
        )
        assert "no-fabrication" not in result.lower() or "Only use verified" not in result

    def test_one_page_selects_no_summary_format(self, settings_manager_isolated, prompt_manager):
        """When enforce_resume_one_page=True, no-summary template is used."""
        sm = settings_manager_isolated
        sm.update({"enforce_resume_one_page": True})
        enforce_one_page = sm.get("enforce_resume_one_page")
        assert enforce_one_page is True

        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE", enforce_one_page=enforce_one_page
        )
        assert "No Summary" in result or "Education" in result

    def test_one_page_off_selects_standard_format(self, settings_manager_isolated, prompt_manager):
        """When enforce_resume_one_page=False, standard template is used."""
        sm = settings_manager_isolated
        sm.update({"enforce_resume_one_page": False})
        enforce_one_page = sm.get("enforce_resume_one_page")

        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE", enforce_one_page=enforce_one_page
        )
        assert "No Summary" not in result

    def test_fabrication_off_selects_no_fab_cover_letter(self, settings_manager_isolated, prompt_manager):
        """When allow_ai_fabrication=False, cover letter uses no-fab variant."""
        sm = settings_manager_isolated
        sm.update({"allow_ai_fabrication": False})
        allow_fab = sm.get("allow_ai_fabrication")

        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="Resume text", job_description="SWE", allow_fabrication=allow_fab
        )
        assert "no-fabrication" in result.lower() or "No invented" in result

    def test_fabrication_off_selects_no_fab_question_prompt(self, settings_manager_isolated, prompt_manager):
        """When allow_ai_fabrication=False, question prompt uses no-fab variant."""
        sm = settings_manager_isolated
        sm.update({"allow_ai_fabrication": False})
        allow_fab = sm.get("allow_ai_fabrication")

        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Why this company?", job_description="SWE", allow_fabrication=allow_fab
        )
        assert "no-fabrication" in result.lower() or "Only real facts" in result

    def test_combined_no_fab_and_one_page(self, settings_manager_isolated, prompt_manager):
        """Both fabrication off and one-page on should work together."""
        sm = settings_manager_isolated
        sm.update({"allow_ai_fabrication": False, "enforce_resume_one_page": True})

        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE",
            allow_fabrication=sm.get("allow_ai_fabrication"),
            enforce_one_page=sm.get("enforce_resume_one_page"),
        )
        # Both features active
        assert "no-fabrication" in result.lower() or "Only use verified" in result
        assert "No Summary" in result or "Education" in result


class TestSettingsPersistence:
    """Test that settings round-trip through save/load correctly."""

    def test_fabrication_setting_persists(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update({"allow_ai_fabrication": False})

        # Reload from file
        sm2 = SettingsManager(settings_file=path)
        assert sm2.settings.allow_ai_fabrication is False

    def test_profile_links_persist(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update(
            {
                "user_linkedin_url": "https://linkedin.com/in/test",
                "user_github_url": "https://github.com/test",
            }
        )

        sm2 = SettingsManager(settings_file=path)
        assert sm2.settings.user_linkedin_url == "https://linkedin.com/in/test"
        assert sm2.settings.user_github_url == "https://github.com/test"

    def test_deepseek_qwen_settings_persist(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update(
            {
                "deepseek_api_key": "sk-deep-test",
                "deepseek_model": "deepseek-coder",
                "qwen_api_key": "sk-qwen-test",
                "qwen_model": "qwen-max",
            }
        )

        sm2 = SettingsManager(settings_file=path)
        assert sm2.settings.deepseek_api_key == "sk-deep-test"
        assert sm2.settings.deepseek_model == "deepseek-coder"
        assert sm2.settings.qwen_api_key == "sk-qwen-test"
        assert sm2.settings.qwen_model == "qwen-max"

    def test_agent_providers_persist(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update({"agent_providers": {"resume_writer": "claude"}})

        sm2 = SettingsManager(settings_file=path)
        assert sm2.settings.agent_providers == {"resume_writer": "claude"}

    def test_validation_settings_persist(self, tmp_path):
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)
        sm.update(
            {
                "enable_contact_replacement": False,
                "enable_text_validation": False,
                "enable_llm_validation": False,
            }
        )

        sm2 = SettingsManager(settings_file=path)
        assert sm2.settings.enable_contact_replacement is False
        assert sm2.settings.enable_text_validation is False
        assert sm2.settings.enable_llm_validation is False


class TestSettingsApiRoundTrip:
    """Test that settings saved via API can be read back correctly."""

    def test_all_fields_round_trip_through_json(self, tmp_path):
        """Verify that all previously-missing fields survive JSON serialization."""
        from services.settings_manager import SettingsManager

        path = tmp_path / "settings.json"
        sm = SettingsManager(settings_file=path)

        all_fields = {
            "allow_ai_fabrication": False,
            "user_linkedin_url": "https://linkedin.com/in/test",
            "user_github_url": "https://github.com/test",
            "deepseek_api_key": "sk-deep",
            "deepseek_model": "deepseek-chat",
            "qwen_api_key": "sk-qwen",
            "qwen_model": "qwen-plus",
            "default_experience_level": "new_grad",
            "enable_contact_replacement": False,
            "enable_text_validation": False,
            "enable_llm_validation": False,
            "agent_providers": {"resume_writer": "claude"},
        }
        sm.update(all_fields)

        # Verify from the file directly
        data = json.loads(path.read_text())
        for key, value in all_fields.items():
            assert key in data, f"Field '{key}' not found in saved JSON"
            assert data[key] == value, f"Field '{key}' has wrong value: {data[key]} != {value}"
