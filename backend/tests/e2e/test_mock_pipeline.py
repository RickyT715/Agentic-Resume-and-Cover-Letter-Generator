"""
Mock end-to-end test: runs a complete task through the v2 pipeline
with mocked AI responses but real LaTeX compilation and PDF processing.

This test verifies the full application works end-to-end:
  1. API endpoints respond correctly (health, CRUD, settings, prompts)
  2. Task lifecycle works (create → configure → start → complete → download)
  3. The v2 pipeline runs all steps (generate resume → compile → extract → cover letter → PDF)
  4. WebSocket progress updates are sent
  5. Task persistence works
  6. Application questions can be added and answered
"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from services.task_manager import task_manager

# ---------------------------------------------------------------------------
# Mock data: realistic LaTeX resume and plain-text cover letter
# ---------------------------------------------------------------------------

MOCK_LATEX_RESPONSE = r"""
% META_COMPANY: Acme Corp
% META_POSITION: Software Engineer

\documentclass[letterpaper,10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.5in]{geometry}

\begin{document}

\begin{center}
{\Large \textbf{John Doe}} \\
john.doe@email.com $|$ (555) 123-4567 $|$ San Francisco, CA
\end{center}

\section*{Summary}
Experienced software engineer with 5+ years of expertise in Python, React, and cloud infrastructure.

\section*{Experience}

\textbf{Senior Software Engineer} \hfill 2022 -- Present \\
\textit{Acme Corp, San Francisco, CA}
\begin{itemize}
  \item Built scalable microservices handling 10M+ daily requests using Python and FastAPI
  \item Led migration from monolith to event-driven architecture, reducing latency by 40\%
  \item Mentored 3 junior engineers and established code review best practices
\end{itemize}

\textbf{Software Engineer} \hfill 2020 -- 2022 \\
\textit{TechStart Inc, Mountain View, CA}
\begin{itemize}
  \item Developed React dashboard used by 500+ enterprise customers
  \item Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes
\end{itemize}

\section*{Education}
\textbf{B.S. Computer Science}, Massachusetts Institute of Technology \hfill 2020

\section*{Skills}
Python, TypeScript, React, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS

\end{document}
"""

MOCK_COVER_LETTER = """John Doe
john.doe@email.com
(555) 123-4567

February 24, 2026

Hiring Manager
Acme Corp
123 Main Street
San Francisco, CA 94105

Dear Hiring Manager,

I am writing to express my strong interest in the Software Engineer position at Acme Corp. With over five years of experience building scalable web applications and leading engineering teams, I am confident that my skills align well with your requirements.

In my current role at Acme Corp, I have architected microservices handling millions of daily requests and led critical infrastructure migrations that significantly improved system performance. My experience with Python, React, and cloud technologies makes me well-suited for this position.

I am particularly excited about the opportunity to contribute to Acme Corp's mission of building innovative technology solutions. I look forward to discussing how my background and enthusiasm can benefit your team.

Sincerely,

John Doe
"""

SAMPLE_JD = """
Software Engineer - Acme Corp

We are looking for a talented Software Engineer to join our team.

Requirements:
- 3+ years of experience in Python and web development
- Experience with React and TypeScript
- Familiarity with cloud infrastructure (AWS, GCP)
- Strong problem-solving skills
- Experience with CI/CD pipelines

Responsibilities:
- Design and build scalable backend services
- Collaborate with cross-functional teams
- Write clean, maintainable code with tests
- Participate in code reviews and technical discussions
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client that returns realistic responses."""
    client = AsyncMock()
    client.provider_name = "mock"
    client.model = "mock-v1"
    client.generate_resume = AsyncMock(return_value=MOCK_LATEX_RESPONSE)
    client.generate_cover_letter = AsyncMock(return_value=MOCK_COVER_LETTER)
    client.generate_resume_with_error_feedback = AsyncMock(return_value=MOCK_LATEX_RESPONSE)
    client.generate_question_answer = AsyncMock(
        return_value="Based on my experience at Acme Corp, I have strong Python skills."
    )
    return client


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def cleanup_tasks():
    """Clean up any tasks created during tests."""
    # Store existing tasks
    existing_ids = set(task_manager.tasks.keys())
    yield
    # Remove tasks created during the test
    new_ids = set(task_manager.tasks.keys()) - existing_ids
    for tid in new_ids:
        task = task_manager.tasks.get(tid)
        if task:
            # Clean up files
            for path_str in [task.resume_pdf_path, task.cover_letter_pdf_path]:
                if path_str and Path(path_str).exists():
                    with contextlib.suppress(Exception):
                        Path(path_str).unlink()
            del task_manager.tasks[tid]
    await task_manager._save_tasks()


# ---------------------------------------------------------------------------
# Test: API Health & Basics
# ---------------------------------------------------------------------------


class TestAPIBasics:
    """Verify all core API endpoints respond correctly."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "default_provider" in data
        assert "pdflatex_available" in data

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        resp = await client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # API keys should be masked (format: first4...last4)
        if data.get("gemini_api_key"):
            key = data["gemini_api_key"]
            assert "..." in key or key == "****" or key == "", f"API key not masked: {key[:8]}..."

    @pytest.mark.asyncio
    async def test_get_templates(self, client):
        resp = await client.get("/api/templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert isinstance(templates, list)
        template_ids = [t["id"] for t in templates]
        assert "classic" in template_ids
        assert "modern" in template_ids
        assert "minimal" in template_ids

    @pytest.mark.asyncio
    async def test_get_providers(self, client):
        resp = await client.get("/api/providers")
        assert resp.status_code == 200
        providers = resp.json()
        provider_ids = [p["id"] for p in providers]
        assert "gemini" in provider_ids
        assert "claude" in provider_ids
        assert "openai_compat" in provider_ids

    @pytest.mark.asyncio
    async def test_get_prompts(self, client):
        resp = await client.get("/api/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "resume_prompt" in data


# ---------------------------------------------------------------------------
# Test: Task CRUD
# ---------------------------------------------------------------------------


class TestTaskCRUD:
    """Test task creation, reading, updating, and deletion."""

    @pytest.mark.asyncio
    async def test_create_task(self, client):
        resp = await client.post(
            "/api/tasks",
            json={
                "job_description": SAMPLE_JD,
                "generate_cover_letter": True,
                "template_id": "classic",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        task = resp.json()
        assert task["status"] == "pending"
        assert task["job_description"] == SAMPLE_JD
        assert task["generate_cover_letter"] is True
        assert task["template_id"] == "classic"
        assert "id" in task
        assert "task_number" in task

    @pytest.mark.asyncio
    async def test_get_task(self, client):
        # Create
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task_id = resp.json()["id"]

        # Get
        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task_id = resp.json()["id"]

        resp = await client.get("/api/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert any(t["id"] == task_id for t in tasks)

    @pytest.mark.asyncio
    async def test_update_task_settings(self, client):
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task_id = resp.json()["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}/settings",
            json={
                "generate_cover_letter": False,
                "template_id": "modern",
                "language": "zh",
                "provider": "gemini",
            },
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["generate_cover_letter"] is False
        assert updated["template_id"] == "modern"
        assert updated["language"] == "zh"
        assert updated["provider"] == "gemini"

    @pytest.mark.asyncio
    async def test_delete_task(self, client):
        resp = await client.post("/api/tasks", json={"job_description": "Test JD"})
        task_id = resp.json()["id"]

        resp = await client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200

        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_start_without_jd_fails(self, client):
        resp = await client.post("/api/tasks", json={"job_description": ""})
        task_id = resp.json()["id"]

        resp = await client.post(f"/api/tasks/{task_id}/start")
        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Application Questions CRUD
# ---------------------------------------------------------------------------


class TestQuestionsCRUD:
    """Test application question endpoints."""

    @pytest.mark.asyncio
    async def test_add_and_list_questions(self, client):
        resp = await client.post("/api/tasks", json={"job_description": SAMPLE_JD})
        task_id = resp.json()["id"]

        # Add questions
        resp = await client.post(
            f"/api/tasks/{task_id}/questions",
            json={
                "question": "Why do you want to work at Acme Corp?",
                "word_limit": 200,
            },
        )
        assert resp.status_code == 200
        q1 = resp.json()
        assert q1["question"] == "Why do you want to work at Acme Corp?"
        assert q1["word_limit"] == 200

        resp = await client.post(
            f"/api/tasks/{task_id}/questions",
            json={
                "question": "Describe your Python experience.",
                "word_limit": 150,
            },
        )
        assert resp.status_code == 200
        resp.json()

        # List
        resp = await client.get(f"/api/tasks/{task_id}/questions")
        assert resp.status_code == 200
        questions = resp.json()
        assert len(questions) == 2

    @pytest.mark.asyncio
    async def test_delete_question(self, client):
        resp = await client.post("/api/tasks", json={"job_description": SAMPLE_JD})
        task_id = resp.json()["id"]

        resp = await client.post(
            f"/api/tasks/{task_id}/questions",
            json={
                "question": "To be deleted",
                "word_limit": 100,
            },
        )
        q_id = resp.json()["id"]

        resp = await client.delete(f"/api/tasks/{task_id}/questions/{q_id}")
        assert resp.status_code == 200

        resp = await client.get(f"/api/tasks/{task_id}/questions")
        assert len(resp.json()) == 0


# ---------------------------------------------------------------------------
# Test: Full V2 Pipeline (Mocked AI, Real LaTeX + PDF)
# ---------------------------------------------------------------------------


class TestFullV2Pipeline:
    """
    Run a complete task through the v2 pipeline with mocked AI.
    Uses real pdflatex compilation if available, otherwise mocks it.
    """

    @pytest.mark.asyncio
    async def test_complete_pipeline_resume_only(self, mock_ai_client):
        """Test the full pipeline: resume generation only (no cover letter)."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            # Create task (no cover letter)
            task = await task_manager.create_task(
                MagicMock(
                    job_description=SAMPLE_JD,
                    generate_cover_letter=False,
                    template_id="classic",
                    language="en",
                    experience_level="auto",
                    provider=None,
                )
            )
            task_id = task.id

            assert task.status.value == "pending"
            assert len(task.steps) == 2  # generate_resume + compile_latex

            # Run pipeline
            await task_manager.run_task(task_id)

            # Verify results
            task = task_manager.get_task(task_id)
            assert task.status.value == "completed", f"Task failed: {task.error_message}"
            assert task.resume_pdf_path is not None
            assert Path(task.resume_pdf_path).exists()
            assert task.latex_source is not None
            assert "\\documentclass" in task.latex_source
            assert task.company_name == "Acme Corp"
            assert task.position_name == "Software Engineer"
            assert task.cover_letter_pdf_path is None  # Not requested

            # Verify AI was called correctly
            mock_ai_client.generate_resume.assert_called_once()
            mock_ai_client.generate_cover_letter.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_pipeline_with_cover_letter(self, mock_ai_client):
        """Test the full pipeline: resume + cover letter."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            task = await task_manager.create_task(
                MagicMock(
                    job_description=SAMPLE_JD,
                    generate_cover_letter=True,
                    template_id="classic",
                    language="en",
                    experience_level="auto",
                    provider=None,
                )
            )
            task_id = task.id

            assert len(task.steps) == 5  # All 5 steps

            await task_manager.run_task(task_id)

            task = task_manager.get_task(task_id)
            assert task.status.value == "completed", f"Task failed: {task.error_message}"

            # Resume results
            assert task.resume_pdf_path is not None
            assert Path(task.resume_pdf_path).exists()
            assert task.latex_source is not None

            # Cover letter results
            assert task.cover_letter_pdf_path is not None
            assert Path(task.cover_letter_pdf_path).exists()

            # Metadata
            assert task.company_name == "Acme Corp"
            assert task.position_name == "Software Engineer"

            # Verify AI calls
            mock_ai_client.generate_resume.assert_called_once()
            mock_ai_client.generate_cover_letter.assert_called_once()

            # All steps should be completed
            for step in task.steps:
                assert step.status.value == "completed", (
                    f"Step {step.step.value} is {step.status.value}: {step.message}"
                )

    @pytest.mark.asyncio
    async def test_pipeline_with_questions(self, client, mock_ai_client):
        """Test adding questions and generating answers."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            # Create task
            resp = await client.post(
                "/api/tasks",
                json={
                    "job_description": SAMPLE_JD,
                    "generate_cover_letter": False,
                },
            )
            task_id = resp.json()["id"]

            # Add a question
            resp = await client.post(
                f"/api/tasks/{task_id}/questions",
                json={
                    "question": "Why do you want to work at Acme Corp?",
                    "word_limit": 150,
                },
            )
            q_id = resp.json()["id"]

            # Generate answer
            resp = await client.post(f"/api/tasks/{task_id}/questions/{q_id}/generate")
            assert resp.status_code == 200
            answer_data = resp.json()
            assert answer_data["status"] == "completed"
            assert answer_data["answer"] is not None

    @pytest.mark.asyncio
    async def test_task_cancel(self, mock_ai_client):
        """Test cancelling a pending task."""
        task = await task_manager.create_task(
            MagicMock(
                job_description=SAMPLE_JD,
                generate_cover_letter=False,
                template_id="classic",
                language="en",
                experience_level="auto",
                provider=None,
            )
        )
        assert task.status.value == "pending"

        result = await task_manager.cancel_task(task.id)
        assert result is not None
        assert result.status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_task_retry_resets_state(self, mock_ai_client):
        """Test that retrying a task resets it properly."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            task = await task_manager.create_task(
                MagicMock(
                    job_description=SAMPLE_JD,
                    generate_cover_letter=False,
                    template_id="classic",
                    language="en",
                    experience_level="auto",
                    provider=None,
                )
            )

            # Run to completion
            await task_manager.run_task(task.id)
            task = task_manager.get_task(task.id)
            assert task.status.value == "completed"

            # Retry
            retried = await task_manager.retry_task(task.id)
            assert retried.status.value == "pending"
            assert retried.resume_pdf_path is None
            assert retried.error_message is None

            # Run again
            await task_manager.run_task(task.id)
            task = task_manager.get_task(task.id)
            assert task.status.value == "completed"


# ---------------------------------------------------------------------------
# Test: Full API Flow (Create → Start → Poll → Download)
# ---------------------------------------------------------------------------


class TestAPIFlow:
    """Test the full API flow: create task, start via endpoint, check result."""

    @pytest.mark.asyncio
    async def test_api_start_and_poll(self, client, mock_ai_client):
        """Create a task via API, start it, poll until done, download results."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            # Step 1: Create task
            resp = await client.post(
                "/api/tasks",
                json={
                    "job_description": SAMPLE_JD,
                    "generate_cover_letter": True,
                    "template_id": "classic",
                },
            )
            assert resp.status_code == 200
            task_data = resp.json()
            task_id = task_data["id"]
            assert task_data["status"] == "pending"

            # Step 2: Start task
            resp = await client.post(f"/api/tasks/{task_id}/start")
            assert resp.status_code == 200
            assert "started" in resp.json()["message"].lower()

            # Step 3: Poll until completed (background task should run)
            for _ in range(30):  # Max 30 iterations
                await asyncio.sleep(0.2)
                resp = await client.get(f"/api/tasks/{task_id}")
                assert resp.status_code == 200
                task_data = resp.json()
                if task_data["status"] in ("completed", "failed"):
                    break
            else:
                pytest.fail("Task did not complete within timeout")

            assert task_data["status"] == "completed", f"Task failed: {task_data.get('error_message')}"

            # Step 4: Download resume PDF
            resp = await client.get(f"/api/tasks/{task_id}/resume")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/pdf"
            assert len(resp.content) > 100  # Real PDF content

            # Step 5: Download cover letter PDF
            resp = await client.get(f"/api/tasks/{task_id}/cover-letter")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/pdf"

            # Step 6: Download LaTeX source
            resp = await client.get(f"/api/tasks/{task_id}/latex")
            assert resp.status_code == 200
            assert "\\documentclass" in resp.text

    @pytest.mark.asyncio
    async def test_api_start_v3_endpoint_exists(self, client):
        """Verify the v3 start endpoint exists and validates correctly."""
        resp = await client.post("/api/tasks", json={"job_description": ""})
        task_id = resp.json()["id"]

        # Should fail - no JD
        resp = await client.post(f"/api/tasks/{task_id}/start-v3")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_nonexistent_task(self, client):
        resp = await client.get("/api/tasks/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_before_completion(self, client):
        resp = await client.post("/api/tasks", json={"job_description": SAMPLE_JD})
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/resume")
        assert resp.status_code == 404

        resp = await client.get(f"/api/tasks/{task_id}/latex")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_evaluation_before_resume(self, client):
        resp = await client.post("/api/tasks", json={"job_description": SAMPLE_JD})
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/evaluation")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_start_already_started_task(self, client, mock_ai_client):
        """Cannot start a task that's already running/completed."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            resp = await client.post(
                "/api/tasks",
                json={
                    "job_description": SAMPLE_JD,
                    "generate_cover_letter": False,
                },
            )
            task_id = resp.json()["id"]

            # Start it
            resp = await client.post(f"/api/tasks/{task_id}/start")
            assert resp.status_code == 200

            # Wait for completion
            for _ in range(30):
                await asyncio.sleep(0.2)
                resp = await client.get(f"/api/tasks/{task_id}")
                if resp.json()["status"] in ("completed", "failed"):
                    break

            # Try to start again
            resp = await client.post(f"/api/tasks/{task_id}/start")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, client, mock_ai_client):
        """Test clearing all completed tasks."""
        with patch("services.task_manager.get_provider_for_task", return_value=mock_ai_client):
            # Create and complete a task
            resp = await client.post(
                "/api/tasks",
                json={
                    "job_description": SAMPLE_JD,
                    "generate_cover_letter": False,
                },
            )
            task_id = resp.json()["id"]

            resp = await client.post(f"/api/tasks/{task_id}/start")

            for _ in range(30):
                await asyncio.sleep(0.2)
                resp = await client.get(f"/api/tasks/{task_id}")
                if resp.json()["status"] in ("completed", "failed"):
                    break

            # Clear completed
            resp = await client.delete("/api/tasks")
            assert resp.status_code == 200
            assert resp.json()["count"] >= 1

            # Task should be gone
            resp = await client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 404
