"""Integration tests: full v3 pipeline with all AI mocked."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.task import Task, TaskStatus

# Mock langgraph before importing the executor
langgraph_mock = MagicMock()
sys.modules.setdefault("langgraph", langgraph_mock)
sys.modules.setdefault("langgraph.graph", langgraph_mock)


def _make_task(**kwargs):
    defaults = dict(
        task_number=1,
        job_description="Looking for a Python developer with 3+ years experience.",
        generate_cover_letter=True,
    )
    defaults.update(kwargs)
    return Task(**defaults)


class TestMockedPipelineFull:
    @pytest.mark.asyncio
    async def test_full_pipeline_resume_only(self):
        """Full pipeline with cover letter disabled."""
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task(generate_cover_letter=False)

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"jd_analysis": {"job_title": "Developer"}, "current_node": "jd_analyzer"}}
            yield {"relevance_matcher": {"relevance_match": {"match_score": 0.8}, "current_node": "relevance_matcher"}}
            yield {
                "resume_writer": {
                    "latex_source": "\\documentclass{a}\\begin{document}\\end{document}",
                    "current_node": "resume_writer",
                }
            }
            yield {"quality_gate": {"quality_passed": True, "current_node": "quality_gate"}}
            yield {"compile_latex": {"resume_pdf_path": "/out/resume.pdf", "current_node": "compile_latex"}}
            yield {"finalize": {"resume_pdf_path": "/out/final_resume.pdf", "current_node": "finalize"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/final_resume.pdf",
                "latex_source": "\\documentclass{a}...",
                "company_name": "TestCo",
                "position_name": "Developer",
            }
        )

        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = "User info"

        with (
            patch("services.langgraph_executor.get_resume_graph", return_value=mock_graph),
            patch("services.langgraph_executor.get_settings_manager", return_value=mock_sm),
            patch("services.langgraph_executor.get_prompt_manager", return_value=mock_pm),
        ):
            result = await run_langgraph_pipeline(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.resume_pdf_path is not None
        assert result.cover_letter_pdf_path is None

    @pytest.mark.asyncio
    async def test_full_pipeline_with_cover_letter(self):
        """Full pipeline with cover letter enabled."""
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task(generate_cover_letter=True)

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"current_node": "jd_analyzer"}}
            yield {"finalize": {"current_node": "finalize"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/resume.pdf",
                "cover_letter_pdf_path": "/out/cover.pdf",
                "latex_source": "tex",
            }
        )

        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = "info"

        with (
            patch("services.langgraph_executor.get_resume_graph", return_value=mock_graph),
            patch("services.langgraph_executor.get_settings_manager", return_value=mock_sm),
            patch("services.langgraph_executor.get_prompt_manager", return_value=mock_pm),
        ):
            result = await run_langgraph_pipeline(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.cover_letter_pdf_path is not None

    @pytest.mark.asyncio
    async def test_pipeline_quality_gate_retry(self):
        """Pipeline where quality gate triggers retry."""
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task(generate_cover_letter=False)

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"current_node": "jd_analyzer"}}
            yield {
                "quality_gate": {
                    "quality_passed": False,
                    "quality_feedback": "Too generic",
                    "current_node": "quality_gate",
                }
            }
            # Second pass after retry
            yield {"resume_writer": {"latex_source": "improved", "current_node": "resume_writer"}}
            yield {"finalize": {"resume_pdf_path": "/out/resume.pdf", "current_node": "finalize"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/resume.pdf",
                "latex_source": "improved tex",
            }
        )

        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = "info"

        with (
            patch("services.langgraph_executor.get_resume_graph", return_value=mock_graph),
            patch("services.langgraph_executor.get_settings_manager", return_value=mock_sm),
            patch("services.langgraph_executor.get_prompt_manager", return_value=mock_pm),
        ):
            result = await run_langgraph_pipeline(task)

        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_pipeline_sets_pipeline_version(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task()

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"finalize": {"current_node": "finalize"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(return_value={"resume_pdf_path": "/out/r.pdf"})

        mock_sm = MagicMock()
        mock_sm.get.return_value = "gemini"
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = "info"

        with (
            patch("services.langgraph_executor.get_resume_graph", return_value=mock_graph),
            patch("services.langgraph_executor.get_settings_manager", return_value=mock_sm),
            patch("services.langgraph_executor.get_prompt_manager", return_value=mock_pm),
        ):
            result = await run_langgraph_pipeline(task)

        assert result.pipeline_version == "v3"
