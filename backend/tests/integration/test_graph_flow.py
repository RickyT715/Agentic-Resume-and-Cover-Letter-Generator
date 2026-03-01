"""Integration tests for the LangGraph pipeline flow.

Tests the graph structure and routing logic with mocked LLM calls.
"""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from agents.state import ResumeState


class TestGraphStructure:
    """Test the graph builds correctly."""

    def test_build_graph(self):
        """Graph compiles without error."""
        from agents.graph import build_resume_graph

        graph = build_resume_graph()
        assert graph is not None

    def test_graph_singleton(self):
        """get_resume_graph returns the same instance."""
        from agents.graph import get_resume_graph

        g1 = get_resume_graph()
        g2 = get_resume_graph()
        assert g1 is g2


class TestQualityGateRouting:
    """Test quality gate conditional routing."""

    def test_should_retry_low_score(self):
        """Low quality score triggers retry."""
        from agents.quality_gate import should_retry

        state: ResumeState = {
            "quality_passed": False,
            "quality_score": 0.4,
            "retry_count": 0,
        }
        assert should_retry(state) == "resume_writer"

    def test_should_not_retry_high_score(self):
        """High quality score proceeds to compilation."""
        from agents.quality_gate import should_retry

        state: ResumeState = {
            "quality_passed": True,
            "quality_score": 0.85,
            "retry_count": 0,
        }
        assert should_retry(state) == "compile_latex"

    def test_should_not_retry_max_retries(self):
        """Max retries exceeded proceeds regardless of score."""
        from agents.quality_gate import should_retry

        state: ResumeState = {
            "quality_passed": False,
            "quality_score": 0.3,
            "retry_count": 2,
        }
        assert should_retry(state) == "compile_latex"


class TestCoverLetterRouting:
    """Test cover letter conditional routing."""

    def test_skip_cover_letter(self):
        """Cover letter is skipped when not requested."""
        from agents.graph import _should_generate_cover_letter

        state: ResumeState = {
            "generate_cover_letter": False,
        }
        assert _should_generate_cover_letter(state) == "finalize"

    def test_generate_cover_letter(self):
        """Cover letter path is taken when requested."""
        from agents.graph import _should_generate_cover_letter

        state: ResumeState = {
            "generate_cover_letter": True,
        }
        assert _should_generate_cover_letter(state) == "extract_text"

    def test_skip_on_error(self):
        """Error state skips to finalize."""
        from agents.graph import _should_generate_cover_letter

        state: ResumeState = {
            "generate_cover_letter": True,
            "error": "Something went wrong",
        }
        assert _should_generate_cover_letter(state) == "finalize"


class TestCompanyResearchRouting:
    """Test RAG retrieval conditional routing."""

    def test_skip_without_company_name(self):
        """No company name means skip retrieval."""
        from agents.graph import _should_retrieve_company

        state: ResumeState = {
            "company_name": "",
            "jd_analysis": {},
        }
        result = _should_retrieve_company(state)
        assert result == "resume_writer"

    def test_skip_without_rag_data(self):
        """Company name but no indexed data means skip."""
        from agents.graph import _should_retrieve_company

        state: ResumeState = {
            "company_name": "TestCorp",
            "jd_analysis": {"company_name": "TestCorp"},
        }
        # Without actual data in vector store, should skip
        result = _should_retrieve_company(state)
        assert result == "resume_writer"


class TestAgentOutputTracking:
    """Test that agent output metadata is tracked correctly."""

    @pytest.mark.asyncio
    async def test_jd_analyzer_tracks_latency(self):
        """JD analyzer should include latency in agent_outputs."""
        from agents.jd_analyzer import jd_analyzer_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value='{"job_title": "SWE", "company_name": "Test", "required_skills": ["Python"], "preferred_skills": [], "experience_level": "mid", "key_responsibilities": ["Code"], "industry": "Tech"}'
        )

        state: ResumeState = {
            "task_id": "test-123",
            "task_number": 1,
            "job_description": "Software engineer at Test Corp. Requires Python.",
            "provider_name": "gemini",
            "agent_outputs": {},
        }

        with patch("agents.jd_analyzer.get_provider", return_value=mock_provider):
            result = await jd_analyzer_agent(state)

        assert "agent_outputs" in result
        assert "jd_analyzer" in result["agent_outputs"]
        assert "latency_ms" in result["agent_outputs"]["jd_analyzer"]
        assert result["jd_analysis"]["job_title"] == "SWE"
