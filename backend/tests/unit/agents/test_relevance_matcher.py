"""Tests for relevance_matcher agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.generate = AsyncMock()
    return provider


class TestRelevanceMatcherAgent:
    @pytest.mark.asyncio
    async def test_parses_valid_json(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = json.dumps(
            {
                "matched_skills": ["Python", "FastAPI"],
                "missing_skills": ["Docker"],
                "relevant_experiences": ["Built REST APIs"],
                "emphasis_points": ["Python expertise"],
                "match_score": 0.85,
            }
        )

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            result = await relevance_matcher_agent(sample_resume_state)

        assert result["relevance_match"]["match_score"] == 0.85
        assert "Python" in result["relevance_match"]["matched_skills"]
        assert result["current_node"] == "relevance_matcher"

    @pytest.mark.asyncio
    async def test_parses_markdown_wrapped_json(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = (
            "```json\n"
            + json.dumps(
                {
                    "matched_skills": ["Python"],
                    "missing_skills": [],
                    "relevant_experiences": [],
                    "emphasis_points": [],
                    "match_score": 0.7,
                }
            )
            + "\n```"
        )

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            result = await relevance_matcher_agent(sample_resume_state)

        assert result["relevance_match"]["match_score"] == 0.7

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = "This is not JSON at all"

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            result = await relevance_matcher_agent(sample_resume_state)

        assert result["relevance_match"]["match_score"] == 0.5
        assert result["relevance_match"]["matched_skills"] == []

    @pytest.mark.asyncio
    async def test_fallback_on_partial_json(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = json.dumps({"matched_skills": ["Go"]})

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            result = await relevance_matcher_agent(sample_resume_state)

        # Should still parse fine since other fields have defaults in schema
        assert "Go" in result["relevance_match"]["matched_skills"]

    @pytest.mark.asyncio
    async def test_records_latency(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = json.dumps(
            {
                "matched_skills": [],
                "missing_skills": [],
                "relevant_experiences": [],
                "emphasis_points": [],
                "match_score": 0.5,
            }
        )

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            result = await relevance_matcher_agent(sample_resume_state)

        assert "relevance_matcher" in result["agent_outputs"]
        assert "latency_ms" in result["agent_outputs"]["relevance_matcher"]

    @pytest.mark.asyncio
    async def test_uses_correct_provider(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = json.dumps(
            {
                "matched_skills": [],
                "missing_skills": [],
                "relevant_experiences": [],
                "emphasis_points": [],
                "match_score": 0.5,
            }
        )

        with patch("services.provider_registry.get_provider", return_value=mock_provider) as mock_get:
            await relevance_matcher_agent(sample_resume_state)
            mock_get.assert_called_once_with("gemini")

    @pytest.mark.asyncio
    async def test_prompt_contains_jd_info(self, sample_resume_state, mock_provider):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider.generate.return_value = json.dumps(
            {
                "matched_skills": [],
                "missing_skills": [],
                "relevant_experiences": [],
                "emphasis_points": [],
                "match_score": 0.5,
            }
        )

        with patch("services.provider_registry.get_provider", return_value=mock_provider):
            await relevance_matcher_agent(sample_resume_state)

        call_args = mock_provider.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Software Engineer" in prompt
        assert "Python" in prompt
