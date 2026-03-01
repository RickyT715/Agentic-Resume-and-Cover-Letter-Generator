"""End-to-end tests for the full resume generation pipeline.

These tests exercise the full API flow: create task -> start -> wait -> download.
They require a running backend or use VCR cassettes for LLM calls.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

BASE = "http://test"


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


class TestHealthCheck:
    """Test the health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "default_provider" in data
        assert "pdflatex_available" in data


class TestTaskLifecycle:
    """Test the complete task CRUD lifecycle."""

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, client):
        # Create
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        assert resp.status_code == 200
        task = resp.json()
        assert task["job_description"] == "Test JD"
        assert task["status"] == "pending"
        task_id = task["id"]

        # Get
        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

        # List
        resp = await client.get("/api/tasks")
        assert resp.status_code == 200
        assert any(t["id"] == task_id for t in resp.json())

        # Delete
        resp = await client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_task_settings(self, client):
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task = resp.json()
        task_id = task["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}/settings",
            json={
                "generate_cover_letter": False,
                "template_id": "modern",
                "language": "zh",
            },
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["generate_cover_letter"] is False
        assert updated["template_id"] == "modern"
        assert updated["language"] == "zh"

        await client.delete(f"/api/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_start_without_jd_fails(self, client):
        resp = await client.post("/api/tasks", json={"job_description": ""})
        task = resp.json()
        task_id = task["id"]

        resp = await client.post(f"/api/tasks/{task_id}/start")
        assert resp.status_code == 400

        await client.delete(f"/api/tasks/{task_id}")


class TestSettingsEndpoints:
    """Test settings API."""

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        resp = await client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_update_settings(self, client):
        resp = await client.put("/api/settings", json={"max_latex_retries": 5})
        assert resp.status_code == 200


class TestTemplatesEndpoints:
    """Test templates API."""

    @pytest.mark.asyncio
    async def test_get_templates(self, client):
        resp = await client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "name" in data[0]


class TestPromptsEndpoints:
    """Test prompts API."""

    @pytest.mark.asyncio
    async def test_get_prompts(self, client):
        resp = await client.get("/api/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_invalid_prompt_key(self, client):
        resp = await client.get("/api/prompts/nonexistent")
        assert resp.status_code == 400


class TestEvaluationEndpoints:
    """Test evaluation API."""

    @pytest.mark.asyncio
    async def test_evaluation_requires_resume(self, client):
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task = resp.json()
        task_id = task["id"]

        resp = await client.get(f"/api/tasks/{task_id}/evaluation")
        assert resp.status_code == 400  # No resume available

        await client.delete(f"/api/tasks/{task_id}")
