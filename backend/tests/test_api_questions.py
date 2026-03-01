"""Tests for application question API endpoints."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_task_manager():
    """Create a mock task manager for API tests."""
    from models.task import ApplicationQuestion, Task

    mock_tm = MagicMock()
    # Create a real task with questions
    task = Task(task_number=1, job_description="Test JD")
    q1 = ApplicationQuestion(id="q1aaaaaa", question="Why here?", word_limit=150)
    task.questions = [q1]
    mock_tm.get_task.return_value = task
    mock_tm.get_all_tasks.return_value = [task]

    return mock_tm, task, q1


@pytest.fixture
def app_with_mock(mock_task_manager):
    """Create a FastAPI app with mocked task_manager."""
    mock_tm, task, q1 = mock_task_manager

    with patch("api.routes.task_manager", mock_tm):
        from fastapi import FastAPI

        from api.routes import router

        app = FastAPI()
        app.include_router(router)
        yield app, mock_tm, task, q1


@pytest.mark.asyncio
class TestGetQuestions:
    async def test_list_questions(self, app_with_mock):
        app, _mock_tm, task, _q1 = app_with_mock
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/questions")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["question"] == "Why here?"

    async def test_list_questions_task_not_found(self, app_with_mock):
        app, mock_tm, _task, _q1 = app_with_mock
        mock_tm.get_task.return_value = None
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/tasks/nonexistent/questions")
        assert r.status_code == 404


@pytest.mark.asyncio
class TestAddQuestion:
    async def test_add_question(self, app_with_mock):
        from models.task import ApplicationQuestion

        app, mock_tm, task, _q1 = app_with_mock
        new_q = ApplicationQuestion(question="New Q", word_limit=200)
        mock_tm.add_question.return_value = new_q

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/tasks/{task.id}/questions",
                json={"question": "New Q", "word_limit": 200},
            )
        assert r.status_code == 200
        assert r.json()["question"] == "New Q"
        assert r.json()["word_limit"] == 200
        mock_tm.add_question.assert_called_once_with(task.id, "New Q", 200)

    async def test_add_question_default_word_limit(self, app_with_mock):
        from models.task import ApplicationQuestion

        app, mock_tm, task, _q1 = app_with_mock
        new_q = ApplicationQuestion(question="Q", word_limit=150)
        mock_tm.add_question.return_value = new_q

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/tasks/{task.id}/questions",
                json={"question": "Q"},
            )
        assert r.status_code == 200
        mock_tm.add_question.assert_called_once_with(task.id, "Q", 150)

    async def test_add_question_task_not_found(self, app_with_mock):
        app, mock_tm, task, _q1 = app_with_mock
        mock_tm.add_question.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/tasks/{task.id}/questions",
                json={"question": "Q"},
            )
        assert r.status_code == 404


@pytest.mark.asyncio
class TestUpdateQuestion:
    async def test_update_question(self, app_with_mock):
        from models.task import ApplicationQuestion

        app, mock_tm, task, q1 = app_with_mock
        updated = ApplicationQuestion(id=q1.id, question="Updated Q", word_limit=200)
        mock_tm.update_question.return_value = updated

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                f"/api/tasks/{task.id}/questions/{q1.id}",
                json={"question": "Updated Q", "word_limit": 200},
            )
        assert r.status_code == 200
        assert r.json()["question"] == "Updated Q"

    async def test_update_question_not_found(self, app_with_mock):
        app, mock_tm, task, _q1 = app_with_mock
        mock_tm.update_question.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put(
                f"/api/tasks/{task.id}/questions/nonexistent",
                json={"question": "Q"},
            )
        assert r.status_code == 404


@pytest.mark.asyncio
class TestDeleteQuestion:
    async def test_delete_question(self, app_with_mock):
        app, mock_tm, task, q1 = app_with_mock
        mock_tm.delete_question.return_value = True

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/api/tasks/{task.id}/questions/{q1.id}")
        assert r.status_code == 200
        assert r.json()["message"] == "Question deleted"

    async def test_delete_question_not_found(self, app_with_mock):
        app, mock_tm, task, _q1 = app_with_mock
        mock_tm.delete_question.return_value = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/api/tasks/{task.id}/questions/nonexistent")
        assert r.status_code == 404


@pytest.mark.asyncio
class TestGenerateQuestionAnswer:
    async def test_generate_answer(self, app_with_mock):
        from models.task import ApplicationQuestion, QuestionStatus

        app, mock_tm, task, q1 = app_with_mock
        answered = ApplicationQuestion(
            id=q1.id,
            question="Why here?",
            answer="Because I love it",
            status=QuestionStatus.COMPLETED,
        )
        mock_tm.generate_question_answer = AsyncMock(return_value=answered)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/questions/{q1.id}/generate")
        assert r.status_code == 200
        assert r.json()["answer"] == "Because I love it"
        assert r.json()["status"] == "completed"

    async def test_generate_requires_job_description(self, app_with_mock):
        app, _mock_tm, task, q1 = app_with_mock
        task.job_description = "   "  # blank

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/questions/{q1.id}/generate")
        assert r.status_code == 400
        assert "Job description is required" in r.json()["detail"]

    async def test_generate_task_not_found(self, app_with_mock):
        app, mock_tm, _task, _q1 = app_with_mock
        mock_tm.get_task.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/tasks/nope/questions/nope/generate")
        assert r.status_code == 404


@pytest.mark.asyncio
class TestGenerateAllAnswers:
    async def test_generate_all(self, app_with_mock):
        from models.task import ApplicationQuestion, QuestionStatus

        app, mock_tm, task, q1 = app_with_mock
        answered = ApplicationQuestion(
            id=q1.id,
            question="Why here?",
            answer="Answer",
            status=QuestionStatus.COMPLETED,
        )
        mock_tm.generate_question_answer = AsyncMock(return_value=answered)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/questions/generate-all")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    async def test_generate_all_requires_job_description(self, app_with_mock):
        app, _mock_tm, task, _q1 = app_with_mock
        task.job_description = ""

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/api/tasks/{task.id}/questions/generate-all")
        assert r.status_code == 400
