"""Unit tests for core API routes (tasks, settings, templates)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.task import Task


@pytest.fixture
def mock_services():
    """Create mock services for API route testing."""
    mock_tm = MagicMock()
    mock_sm = MagicMock()
    mock_pm = MagicMock()

    # Task manager defaults
    task = Task(task_number=1, job_description="Test JD")
    mock_tm.get_task.return_value = task
    mock_tm.get_all_tasks.return_value = [task]
    mock_tm.create_task.return_value = task

    # Settings manager defaults
    mock_sm.get_all.return_value = {"default_provider": "gemini"}
    mock_sm.get.return_value = "gemini"

    # Prompt manager defaults
    mock_pm.get_all_prompts.return_value = {"resume_prompt": "test"}
    mock_pm.get_prompt.return_value = "test prompt"
    mock_pm.validate_prompt.return_value = []
    mock_pm.update_prompt.return_value = True

    return mock_tm, mock_sm, mock_pm, task


@pytest.fixture
def app_with_mocks(mock_services):
    """Create a FastAPI app with all services mocked."""
    mock_tm, mock_sm, mock_pm, task = mock_services

    with (
        patch("api.routes.task_manager", mock_tm),
        patch("api.routes.get_settings_manager", return_value=mock_sm),
        patch("api.routes.get_prompt_manager", return_value=mock_pm),
    ):
        from fastapi import FastAPI

        from api.routes import router

        app = FastAPI()
        app.include_router(router)
        yield app, mock_tm, mock_sm, mock_pm, task


@pytest.mark.asyncio
class TestTaskEndpoints:
    async def test_create_task(self, app_with_mocks):
        app, mock_tm, *_ = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/tasks", json={"job_description": "SWE at Google"})
        assert r.status_code == 200
        mock_tm.create_task.assert_called_once()

    async def test_get_all_tasks(self, app_with_mocks):
        app, _mock_tm, *_ = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/tasks")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    async def test_get_task_by_id(self, app_with_mocks):
        app, _mock_tm, _, _, task = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}")
        assert r.status_code == 200

    async def test_get_task_not_found(self, app_with_mocks):
        app, mock_tm, *_ = app_with_mocks
        mock_tm.get_task.return_value = None
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/tasks/nonexistent")
        assert r.status_code == 404

    async def test_delete_task(self, app_with_mocks):
        app, mock_tm, _, _, task = app_with_mocks
        mock_tm.delete_task.return_value = True
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/api/tasks/{task.id}")
        assert r.status_code == 200

    async def test_delete_task_not_found(self, app_with_mocks):
        app, mock_tm, *_ = app_with_mocks
        mock_tm.delete_task.return_value = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete("/api/tasks/nonexistent")
        assert r.status_code == 400

    async def test_start_task(self, app_with_mocks):
        app, _mock_tm, _, _, task = app_with_mocks
        task.job_description = "Valid JD"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/start")
        assert r.status_code == 200

    async def test_start_task_empty_jd(self, app_with_mocks):
        app, _mock_tm, _, _, task = app_with_mocks
        task.job_description = "   "
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/start")
        assert r.status_code == 400

    async def test_cancel_task(self, app_with_mocks):
        app, mock_tm, _, _, task = app_with_mocks
        mock_tm.cancel_task.return_value = task
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/cancel")
        assert r.status_code == 200

    async def test_retry_task(self, app_with_mocks):
        app, mock_tm, _, _, task = app_with_mocks
        mock_tm.retry_task.return_value = task
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/retry")
        assert r.status_code == 200


@pytest.mark.asyncio
class TestSettingsEndpoints:
    async def test_get_settings(self, app_with_mocks):
        app, _, mock_sm, *_ = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/settings")
        assert r.status_code == 200
        mock_sm.get_all.assert_called_with(mask_api_key=True)


@pytest.mark.asyncio
class TestPromptsEndpoints:
    async def test_get_prompts(self, app_with_mocks):
        app, _, _, _mock_pm, _ = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/prompts")
        assert r.status_code == 200

    async def test_get_invalid_prompt_key(self, app_with_mocks):
        app, *_ = app_with_mocks
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/prompts/invalid_key")
        assert r.status_code == 400


@pytest.mark.asyncio
class TestTemplateEndpoints:
    async def test_get_templates(self, app_with_mocks):
        app, mock_tm, *_ = app_with_mocks
        mock_tm.get_available_templates.return_value = [
            {"id": "classic", "name": "Classic"},
        ]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/templates")
        assert r.status_code == 200
