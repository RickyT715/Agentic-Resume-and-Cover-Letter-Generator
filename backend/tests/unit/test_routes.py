"""Unit tests for core API routes (tasks, settings, templates)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    # These are now async in TaskManager
    mock_tm.create_task = AsyncMock(return_value=task)
    mock_tm.delete_task = AsyncMock(return_value=True)
    mock_tm.delete_completed_tasks = AsyncMock(return_value=0)
    mock_tm.cancel_task = AsyncMock(return_value=task)
    mock_tm.retry_task = AsyncMock(return_value=task)
    mock_tm.update_task_job_description = AsyncMock(return_value=task)
    mock_tm.update_task_settings = AsyncMock(return_value=task)

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
        mock_tm.delete_task = AsyncMock(return_value=True)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/api/tasks/{task.id}")
        assert r.status_code == 200

    async def test_delete_task_not_found(self, app_with_mocks):
        app, mock_tm, *_ = app_with_mocks
        mock_tm.delete_task = AsyncMock(return_value=False)
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
        mock_tm.cancel_task = AsyncMock(return_value=task)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/cancel")
        assert r.status_code == 200

    async def test_retry_task(self, app_with_mocks):
        app, mock_tm, _, _, task = app_with_mocks
        mock_tm.retry_task = AsyncMock(return_value=task)
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

    async def test_update_settings_basic(self, app_with_mocks):
        """PUT /api/settings with basic fields should succeed."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {"default_provider": "claude"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put("/api/settings", json={"default_provider": "claude", "max_latex_retries": 5})
        assert r.status_code == 200
        mock_sm.update.assert_called_once()

    async def test_update_settings_allow_ai_fabrication(self, app_with_mocks):
        """PUT /api/settings should accept allow_ai_fabrication field."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {"allow_ai_fabrication": False}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put("/api/settings", json={"allow_ai_fabrication": False})
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert "allow_ai_fabrication" in call_args
        assert call_args["allow_ai_fabrication"] is False

    async def test_update_settings_user_profile_links(self, app_with_mocks):
        """PUT /api/settings should accept user profile link fields."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                "/api/settings",
                json={
                    "user_linkedin_url": "https://linkedin.com/in/test",
                    "user_github_url": "https://github.com/test",
                },
            )
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["user_linkedin_url"] == "https://linkedin.com/in/test"
        assert call_args["user_github_url"] == "https://github.com/test"

    async def test_update_settings_deepseek_fields(self, app_with_mocks):
        """PUT /api/settings should accept DeepSeek provider fields."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                "/api/settings",
                json={
                    "deepseek_api_key": "sk-deep-123",
                    "deepseek_model": "deepseek-chat",
                    "deepseek_temperature": 0.7,
                    "deepseek_max_output_tokens": 4096,
                },
            )
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["deepseek_api_key"] == "sk-deep-123"
        assert call_args["deepseek_model"] == "deepseek-chat"

    async def test_update_settings_qwen_fields(self, app_with_mocks):
        """PUT /api/settings should accept Qwen provider fields."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                "/api/settings",
                json={
                    "qwen_api_key": "sk-qwen-456",
                    "qwen_model": "qwen-plus",
                    "qwen_temperature": 0.5,
                    "qwen_max_output_tokens": 8192,
                },
            )
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["qwen_api_key"] == "sk-qwen-456"
        assert call_args["qwen_model"] == "qwen-plus"

    async def test_update_settings_validation_fields(self, app_with_mocks):
        """PUT /api/settings should accept resume validation fields."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                "/api/settings",
                json={
                    "enable_contact_replacement": False,
                    "enable_text_validation": False,
                    "enable_llm_validation": False,
                },
            )
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["enable_contact_replacement"] is False
        assert call_args["enable_text_validation"] is False
        assert call_args["enable_llm_validation"] is False

    async def test_update_settings_agent_providers(self, app_with_mocks):
        """PUT /api/settings should accept agent_providers dict."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                "/api/settings",
                json={"agent_providers": {"resume_writer": "claude", "jd_analyzer": "gemini"}},
            )
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["agent_providers"] == {"resume_writer": "claude", "jd_analyzer": "gemini"}

    async def test_update_settings_experience_level(self, app_with_mocks):
        """PUT /api/settings should accept default_experience_level."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put("/api/settings", json={"default_experience_level": "new_grad"})
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        assert call_args["default_experience_level"] == "new_grad"

    async def test_update_settings_all_previously_missing_fields(self, app_with_mocks):
        """PUT /api/settings should accept ALL fields that were previously missing."""
        app, _, mock_sm, *_ = app_with_mocks
        mock_sm.update.return_value = MagicMock()
        mock_sm.get_all.return_value = {}
        all_fields = {
            "deepseek_api_key": "sk-deep",
            "deepseek_model": "deepseek-chat",
            "deepseek_temperature": 0.7,
            "deepseek_max_output_tokens": 4096,
            "qwen_api_key": "sk-qwen",
            "qwen_model": "qwen-plus",
            "qwen_temperature": 0.5,
            "qwen_max_output_tokens": 8192,
            "default_experience_level": "experienced",
            "allow_ai_fabrication": False,
            "enable_contact_replacement": True,
            "enable_text_validation": True,
            "enable_llm_validation": False,
            "user_linkedin_url": "https://linkedin.com/in/user",
            "user_github_url": "https://github.com/user",
            "agent_providers": {"resume_writer": "claude"},
        }
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put("/api/settings", json=all_fields)
        assert r.status_code == 200
        call_args = mock_sm.update.call_args[0][0]
        # Verify none of the fields were silently dropped
        for key, value in all_fields.items():
            assert key in call_args, f"Field '{key}' was dropped by AppSettingsUpdate model"
            assert call_args[key] == value, f"Field '{key}' has wrong value"


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
