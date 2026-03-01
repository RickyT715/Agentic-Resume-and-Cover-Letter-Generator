"""Tests for cover_letter_writer agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.generate = AsyncMock(return_value="Dear Hiring Manager,\n\nI am writing to express my interest...")
    return provider


@pytest.fixture
def mock_prompt_manager():
    pm = MagicMock()
    pm.get_cover_letter_prompt_with_substitutions.return_value = "Base cover letter prompt"
    return pm


@pytest.fixture
def cover_letter_state(sample_resume_state):
    state = dict(sample_resume_state)
    state["resume_text"] = "Software Engineer with 5 years experience in Python and FastAPI."
    return state


class TestCoverLetterWriterAgent:
    @pytest.mark.asyncio
    async def test_generates_cover_letter(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await cover_letter_writer_agent(cover_letter_state)

        assert "cover_letter_text" in result
        assert "Dear Hiring Manager" in result["cover_letter_text"]

    @pytest.mark.asyncio
    async def test_sets_current_node(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await cover_letter_writer_agent(cover_letter_state)

        assert result["current_node"] == "cover_letter_writer"

    @pytest.mark.asyncio
    async def test_records_agent_outputs(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            result = await cover_letter_writer_agent(cover_letter_state)

        assert "cover_letter_writer" in result["agent_outputs"]
        assert "latency_ms" in result["agent_outputs"]["cover_letter_writer"]
        assert "text_length" in result["agent_outputs"]["cover_letter_writer"]

    @pytest.mark.asyncio
    async def test_prompt_includes_jd_analysis(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            await cover_letter_writer_agent(cover_letter_state)

        call_args = mock_provider.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Software Engineer" in prompt
        assert "TestCo" in prompt

    @pytest.mark.asyncio
    async def test_includes_company_context(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        cover_letter_state["company_context"] = "TestCo values innovation and collaboration."

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            await cover_letter_writer_agent(cover_letter_state)

        call_args = mock_provider.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "innovation and collaboration" in prompt

    @pytest.mark.asyncio
    async def test_uses_correct_provider(self, cover_letter_state, mock_provider, mock_prompt_manager):
        from agents.cover_letter_writer import cover_letter_writer_agent

        with (
            patch("services.provider_registry.get_provider", return_value=mock_provider) as mock_get,
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_prompt_manager),
        ):
            await cover_letter_writer_agent(cover_letter_state)
            mock_get.assert_called_once_with("gemini")
