"""Tests for the JD Analyzer agent."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agents.jd_analyzer import jd_analyzer_agent


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def base_state():
    return {
        "task_id": "test123",
        "task_number": 1,
        "job_description": "Software Engineer at Google. Python, Go required. 3+ years experience.",
        "provider_name": "gemini",
        "agent_outputs": {},
    }


class TestJDAnalyzer:
    @pytest.mark.asyncio
    async def test_parses_valid_json(self, mock_provider, base_state):
        mock_provider.generate.return_value = json.dumps({
            "job_title": "Software Engineer",
            "company_name": "Google",
            "required_skills": ["Python", "Go"],
            "preferred_skills": ["Kubernetes"],
            "experience_level": "3+ years",
            "key_responsibilities": ["Build systems"],
            "industry": "Technology",
        })

        with patch("agents.jd_analyzer.get_provider", return_value=mock_provider):
            result = await jd_analyzer_agent(base_state)

        assert result["jd_analysis"]["job_title"] == "Software Engineer"
        assert result["jd_analysis"]["company_name"] == "Google"
        assert "Python" in result["jd_analysis"]["required_skills"]
        assert result["company_name"] == "Google"
        assert result["position_name"] == "Software Engineer"
        assert result["current_node"] == "jd_analyzer"

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self, mock_provider, base_state):
        mock_provider.generate.return_value = """```json
{
    "job_title": "Backend Dev",
    "company_name": "Meta",
    "required_skills": ["Java"],
    "preferred_skills": [],
    "experience_level": "5 years",
    "key_responsibilities": [],
    "industry": "Tech"
}
```"""

        with patch("agents.jd_analyzer.get_provider", return_value=mock_provider):
            result = await jd_analyzer_agent(base_state)

        assert result["jd_analysis"]["job_title"] == "Backend Dev"

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, mock_provider, base_state):
        mock_provider.generate.return_value = "This is not valid JSON at all."

        with patch("agents.jd_analyzer.get_provider", return_value=mock_provider):
            result = await jd_analyzer_agent(base_state)

        assert result["jd_analysis"]["job_title"] == "Unknown Position"
        assert result["current_node"] == "jd_analyzer"

    @pytest.mark.asyncio
    async def test_tracks_latency(self, mock_provider, base_state):
        mock_provider.generate.return_value = json.dumps({
            "job_title": "SWE",
            "company_name": "",
            "required_skills": [],
            "preferred_skills": [],
            "experience_level": "",
            "key_responsibilities": [],
            "industry": "",
        })

        with patch("agents.jd_analyzer.get_provider", return_value=mock_provider):
            result = await jd_analyzer_agent(base_state)

        assert "jd_analyzer" in result["agent_outputs"]
        assert "latency_ms" in result["agent_outputs"]["jd_analyzer"]
