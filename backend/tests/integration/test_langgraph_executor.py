"""Integration tests for the LangGraph executor service."""

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
        job_description="We need a Python engineer.",
        generate_cover_letter=True,
    )
    defaults.update(kwargs)
    return Task(**defaults)


class TestRunLanggraphPipeline:
    @pytest.mark.asyncio
    async def test_successful_pipeline(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task()

        # Mock the graph to return a successful final state
        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"jd_analysis": {}, "current_node": "jd_analyzer"}}
            yield {"resume_writer": {"latex_source": "tex", "current_node": "resume_writer"}}
            yield {"finalize": {"resume_pdf_path": "/out/resume.pdf", "current_node": "finalize"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/resume.pdf",
                "latex_source": "\\documentclass{article}...",
                "company_name": "TestCo",
                "position_name": "Engineer",
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
        assert result.resume_pdf_path == "/out/resume.pdf"
        assert result.company_name == "TestCo"

    @pytest.mark.asyncio
    async def test_pipeline_with_error(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task()

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"current_node": "jd_analyzer"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "error": "LaTeX compilation failed",
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

        assert result.status == TaskStatus.FAILED
        assert "LaTeX" in result.error_message

    @pytest.mark.asyncio
    async def test_pipeline_exception(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task()

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            raise RuntimeError("Graph exploded")
            yield  # make this an async generator

        mock_graph.astream = fake_astream

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

        assert result.status == TaskStatus.FAILED
        assert "exploded" in result.error_message

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task()
        progress_updates = []

        async def track_progress(update):
            progress_updates.append(update)

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"jd_analyzer": {"current_node": "jd_analyzer"}}
            yield {"resume_writer": {"current_node": "resume_writer"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/resume.pdf",
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
            await run_langgraph_pipeline(task, progress_callback=track_progress)

        # Should have progress updates for nodes + final
        assert len(progress_updates) >= 2
        assert any(u.get("node") == "jd_analyzer" for u in progress_updates)

    @pytest.mark.asyncio
    async def test_step_tracking(self):
        from services.langgraph_executor import run_langgraph_pipeline

        task = _make_task(generate_cover_letter=False)

        mock_graph = AsyncMock()

        async def fake_astream(state, **kwargs):
            yield {"compile_latex": {"current_node": "compile_latex"}}

        mock_graph.astream = fake_astream
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "resume_pdf_path": "/out/resume.pdf",
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
        assert result.completed_at is not None
