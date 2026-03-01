"""Tests for PDF inline preview vs attachment download."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_task_with_pdf(tmp_path):
    """Create a mock task manager with a task that has a real PDF file."""
    from models.task import Task

    # Create a minimal valid PDF file
    pdf_path = tmp_path / "resume_test.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n109\n%%EOF\n"
    )

    mock_tm = MagicMock()
    task = Task(task_number=1, job_description="Test JD")
    task.resume_pdf_path = str(pdf_path)
    task.cover_letter_pdf_path = str(pdf_path)
    mock_tm.get_task.return_value = task

    return mock_tm, task, pdf_path


@pytest.fixture
def app_with_pdf(mock_task_with_pdf):
    """Create a FastAPI app with mocked task_manager that has PDF files."""
    mock_tm, task, pdf_path = mock_task_with_pdf

    with patch("api.routes.task_manager", mock_tm):
        from fastapi import FastAPI

        from api.routes import router

        app = FastAPI()
        app.include_router(router)
        yield app, mock_tm, task, pdf_path


@pytest.mark.asyncio
class TestResumeDownloadDisposition:
    async def test_default_is_attachment(self, app_with_pdf):
        """Without ?inline, Content-Disposition should be 'attachment'."""
        app, _mock_tm, task, pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/resume")
        assert r.status_code == 200
        cd = r.headers["content-disposition"]
        assert cd.startswith("attachment")
        assert pdf_path.name in cd

    async def test_inline_true_sets_inline_disposition(self, app_with_pdf):
        """With ?inline=true, Content-Disposition should be 'inline'."""
        app, _mock_tm, task, pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/resume?inline=true")
        assert r.status_code == 200
        cd = r.headers["content-disposition"]
        assert cd.startswith("inline")
        assert pdf_path.name in cd

    async def test_inline_false_is_attachment(self, app_with_pdf):
        """With ?inline=false, Content-Disposition should be 'attachment'."""
        app, _mock_tm, task, _pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/resume?inline=false")
        assert r.status_code == 200
        cd = r.headers["content-disposition"]
        assert cd.startswith("attachment")

    async def test_content_type_is_pdf(self, app_with_pdf):
        """Both inline and attachment should return application/pdf."""
        app, _mock_tm, task, _pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.get(f"/api/tasks/{task.id}/resume")
            r2 = await client.get(f"/api/tasks/{task.id}/resume?inline=true")
        assert r1.headers["content-type"] == "application/pdf"
        assert r2.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
class TestCoverLetterDownloadDisposition:
    async def test_default_is_attachment(self, app_with_pdf):
        app, _mock_tm, task, _pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/cover-letter")
        assert r.status_code == 200
        cd = r.headers["content-disposition"]
        assert cd.startswith("attachment")

    async def test_inline_true_sets_inline_disposition(self, app_with_pdf):
        app, _mock_tm, task, pdf_path = app_with_pdf
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/tasks/{task.id}/cover-letter?inline=true")
        assert r.status_code == 200
        cd = r.headers["content-disposition"]
        assert cd.startswith("inline")
        assert pdf_path.name in cd
