"""Unit tests for TaskManager core CRUD and persistence logic."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.task import TaskCreate, TaskStatus, TaskStep


@pytest.mark.asyncio
class TestCreateTask:
    async def test_creates_task_with_defaults(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="Software Engineer at Acme"))
        assert task.task_number == 1
        assert task.job_description == "Software Engineer at Acme"
        assert task.status == TaskStatus.PENDING
        assert task.generate_cover_letter is True
        assert task.template_id == "classic"
        assert task.language == "en"
        assert task.provider is None

    async def test_increments_task_counter(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = await tm.create_task(TaskCreate(job_description="JD1"))
        t2 = await tm.create_task(TaskCreate(job_description="JD2"))
        assert t1.task_number == 1
        assert t2.task_number == 2

    async def test_creates_correct_steps_with_cover_letter(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD", generate_cover_letter=True))
        step_names = [s.step for s in task.steps]
        assert TaskStep.GENERATE_RESUME in step_names
        assert TaskStep.COMPILE_LATEX in step_names
        assert TaskStep.EXTRACT_TEXT in step_names
        assert TaskStep.GENERATE_COVER_LETTER in step_names
        assert TaskStep.CREATE_COVER_PDF in step_names

    async def test_creates_correct_steps_without_cover_letter(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD", generate_cover_letter=False))
        step_names = [s.step for s in task.steps]
        assert TaskStep.GENERATE_RESUME in step_names
        assert TaskStep.COMPILE_LATEX in step_names
        assert TaskStep.EXTRACT_TEXT not in step_names

    async def test_task_stored_in_manager(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        assert tm.get_task(task.id) is task

    async def test_custom_template_id(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD", template_id="modern"))
        assert task.template_id == "modern"

    async def test_custom_language(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD", language="zh"))
        assert task.language == "zh"

    async def test_custom_provider(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD", provider="claude"))
        assert task.provider == "claude"


@pytest.mark.asyncio
class TestGetTask:
    async def test_returns_task_by_id(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        assert tm.get_task(task.id) is task

    def test_returns_none_for_missing(self, task_manager_isolated):
        assert task_manager_isolated.get_task("nonexistent") is None


@pytest.mark.asyncio
class TestGetAllTasks:
    async def test_returns_all_tasks(self, task_manager_isolated):
        tm = task_manager_isolated
        await tm.create_task(TaskCreate(job_description="JD1"))
        await tm.create_task(TaskCreate(job_description="JD2"))
        tasks = tm.get_all_tasks()
        assert len(tasks) == 2

    def test_returns_empty_when_no_tasks(self, task_manager_isolated):
        assert task_manager_isolated.get_all_tasks() == []


@pytest.mark.asyncio
class TestDeleteTask:
    async def test_deletes_existing_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        assert await tm.delete_task(task.id) is True
        assert tm.get_task(task.id) is None

    async def test_cannot_delete_running_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        assert await tm.delete_task(task.id) is False

    async def test_returns_false_for_missing_task(self, task_manager_isolated):
        assert await task_manager_isolated.delete_task("nonexistent") is False


@pytest.mark.asyncio
class TestDeleteCompletedTasks:
    async def test_deletes_completed_and_failed_tasks(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = await tm.create_task(TaskCreate(job_description="JD1"))
        t2 = await tm.create_task(TaskCreate(job_description="JD2"))
        t3 = await tm.create_task(TaskCreate(job_description="JD3"))
        t1.status = TaskStatus.COMPLETED
        t2.status = TaskStatus.FAILED
        t3.status = TaskStatus.PENDING

        count = await tm.delete_completed_tasks()
        assert count == 2
        assert tm.get_task(t1.id) is None
        assert tm.get_task(t2.id) is None
        assert tm.get_task(t3.id) is not None


@pytest.mark.asyncio
class TestRetryTask:
    async def test_resets_failed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.FAILED
        task.error_message = "Some error"
        task.resume_pdf_path = "/some/path.pdf"

        retried = await tm.retry_task(task.id)
        assert retried is not None
        assert retried.status == TaskStatus.PENDING
        assert retried.error_message is None
        assert retried.resume_pdf_path is None

    async def test_cannot_retry_running_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        assert await tm.retry_task(task.id) is None

    async def test_cannot_retry_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        assert await tm.retry_task(task.id) is None

    async def test_returns_none_for_missing_task(self, task_manager_isolated):
        assert await task_manager_isolated.retry_task("nonexistent") is None


@pytest.mark.asyncio
class TestCancelTask:
    async def test_cancels_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.cancel_task(task.id)
        assert result is not None
        assert result.cancelled is True
        assert result.status == TaskStatus.CANCELLED

    async def test_marks_running_task_for_cancellation(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        result = await tm.cancel_task(task.id)
        assert result is not None
        assert result.cancelled is True
        # Running task stays running until the loop checks

    async def test_cannot_cancel_completed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.COMPLETED
        assert await tm.cancel_task(task.id) is None


@pytest.mark.asyncio
class TestUpdateTaskSettings:
    async def test_update_job_description(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="Old JD"))
        result = await tm.update_task_settings(task.id, job_description="New JD")
        assert result.job_description == "New JD"

    async def test_update_template(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.update_task_settings(task.id, template_id="modern")
        assert result.template_id == "modern"

    async def test_cannot_update_started_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        result = await tm.update_task_settings(task.id, job_description="New JD")
        assert result is None


@pytest.mark.asyncio
class TestTaskPersistence:
    async def test_tasks_saved_to_disk(self, task_manager_isolated, tmp_path):
        tm = task_manager_isolated
        await tm.create_task(TaskCreate(job_description="Persisted JD"))

        data_dir = tmp_path / "data"
        tasks_file = data_dir / "tasks.json"
        assert tasks_file.exists()

        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        assert data["task_counter"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["job_description"] == "Persisted JD"


class TestJDHistory:
    def test_save_and_load_jd_history(self, task_manager_isolated):
        tm = task_manager_isolated
        tm._save_jd_to_history("Software Engineer at Google")
        history = tm.get_jd_history()
        assert len(history) == 1
        assert history[0]["text"] == "Software Engineer at Google"

    def test_deduplicates_jd_history(self, task_manager_isolated):
        tm = task_manager_isolated
        tm._save_jd_to_history("Same JD")
        tm._save_jd_to_history("Different JD")
        tm._save_jd_to_history("Same JD")
        history = tm.get_jd_history()
        assert len(history) == 2
        assert history[0]["text"] == "Same JD"

    def test_limits_jd_history_to_20(self, task_manager_isolated):
        tm = task_manager_isolated
        for i in range(25):
            tm._save_jd_to_history(f"JD {i}")
        history = tm.get_jd_history()
        assert len(history) == 20

    def test_empty_jd_not_saved(self, task_manager_isolated):
        tm = task_manager_isolated
        tm._save_jd_to_history("   ")
        assert tm.get_jd_history() == []


class TestTemplates:
    def test_returns_available_templates(self, task_manager_isolated):
        templates = task_manager_isolated.get_available_templates()
        assert len(templates) == 3
        ids = [t["id"] for t in templates]
        assert "classic" in ids
        assert "modern" in ids
        assert "minimal" in ids


class TestSanitizeFilename:
    def test_basic_sanitize(self, task_manager_isolated):
        result = task_manager_isolated._sanitize_filename("Google Inc.")
        assert result == "Google_Inc."

    def test_special_characters_removed(self, task_manager_isolated):
        result = task_manager_isolated._sanitize_filename('Test<>:"/\\|?*Name')
        assert "<" not in result
        assert ">" not in result

    def test_spaces_to_underscores(self, task_manager_isolated):
        result = task_manager_isolated._sanitize_filename("Acme Corp Position")
        assert " " not in result
        assert "_" in result

    def test_long_name_truncated(self, task_manager_isolated):
        long_name = "A" * 100
        result = task_manager_isolated._sanitize_filename(long_name)
        assert len(result) <= 50

    def test_empty_string_returns_fallback(self, task_manager_isolated):
        result = task_manager_isolated._sanitize_filename("")
        assert result == "Unknown_Company"
