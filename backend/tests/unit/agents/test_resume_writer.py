"""Tests for resume_writer agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.generate = AsyncMock(
        return_value=(
            "% META_COMPANY: TestCo\n"
            "% META_POSITION: Software Engineer\n"
            "\\documentclass[letterpaper,10pt]{article}\n"
            "\\begin{document}\n"
            "Resume content here\n"
            "\\end{document}"
        )
    )
    return provider


@pytest.fixture
def mock_prompt_manager():
    pm = MagicMock()
    pm.get_resume_prompt_with_substitutions.return_value = "Base resume prompt"
    pm.get_prompt.return_value = "John Doe\nEmail: john@example.com\nMobile: 555-1234"
    return pm


class TestResumeWriterAgent:
    @pytest.mark.asyncio
    async def test_generates_latex(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert "latex_source" in result
        assert result["latex_source"].startswith("\\documentclass")
        assert result["latex_source"].endswith("\\end{document}")

    @pytest.mark.asyncio
    async def test_extracts_metadata(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert result.get("company_name") == "TestCo"
        assert result.get("position_name") == "Software Engineer"

    @pytest.mark.asyncio
    async def test_sets_current_node(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert result["current_node"] == "resume_writer"

    @pytest.mark.asyncio
    async def test_records_agent_outputs(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert "resume_writer" in result["agent_outputs"]
        assert "latency_ms" in result["agent_outputs"]["resume_writer"]
        assert "latex_length" in result["agent_outputs"]["resume_writer"]

    @pytest.mark.asyncio
    async def test_includes_quality_feedback_on_retry(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        sample_resume_state["quality_feedback"] = "Needs more keywords"
        sample_resume_state["quality_score"] = 0.4
        sample_resume_state["retry_count"] = 1

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            await resume_writer_agent(sample_resume_state)

        # The prompt should have been constructed with feedback
        call_args = mock_provider.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Needs more keywords" in prompt

    @pytest.mark.asyncio
    async def test_includes_company_context(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        sample_resume_state["company_context"] = "TestCo is a leading AI company founded in 2020."

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            await resume_writer_agent(sample_resume_state)

        call_args = mock_provider.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "leading AI company" in prompt

    @pytest.mark.asyncio
    async def test_saves_resume_prompt(self, sample_resume_state, mock_provider, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert "resume_prompt" in result
        assert len(result["resume_prompt"]) > 0

    @pytest.mark.asyncio
    async def test_no_metadata_when_absent(self, sample_resume_state, mock_prompt_manager):
        from agents.resume_writer import resume_writer_agent

        provider = AsyncMock()
        provider.generate = AsyncMock(
            return_value=("\\documentclass[letterpaper,10pt]{article}\n\\begin{document}\nContent\n\\end{document}")
        )

        with (
            patch("services.provider_registry.get_provider", return_value=provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await resume_writer_agent(sample_resume_state)

        assert "company_name" not in result
        assert "position_name" not in result
