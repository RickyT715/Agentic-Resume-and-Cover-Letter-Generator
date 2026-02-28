"""Integration tests for task state machine transitions."""
import asyncio
import pytest
from models.task import TaskCreate, TaskStatus


class TestTaskCreation:
    def test_create_task_increments_counter(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = tm.create_task(TaskCreate(job_description="JD1"))
        t2 = tm.create_task(TaskCreate(job_description="JD2"))
        assert t1.task_number == 1
        assert t2.task_number == 2

    def test_create_task_default_status(self, task_manager_isolated):
        task = task_manager_isolated.create_task(TaskCreate(job_description="JD"))
        assert task.status == TaskStatus.PENDING

    def test_create_task_with_cover_letter(self, task_manager_isolated):
        task = task_manager_isolated.create_task(
            TaskCreate(job_description="JD", generate_cover_letter=True)
        )
        assert task.generate_cover_letter is True
        assert len(task.steps) == 5

    def test_create_task_without_cover_letter(self, task_manager_isolated):
        task = task_manager_isolated.create_task(
            TaskCreate(job_description="JD", generate_cover_letter=False)
        )
        assert task.generate_cover_letter is False
        assert len(task.steps) == 2


class TestTaskRetry:
    def test_retry_failed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.FAILED
        tm._save_tasks()

        retried = tm.retry_task(task.id)
        assert retried is not None
        assert retried.status == TaskStatus.PENDING
        assert retried.error_message is None

    def test_retry_completed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.COMPLETED
        tm._save_tasks()

        retried = tm.retry_task(task.id)
        assert retried is not None
        assert retried.status == TaskStatus.PENDING

    def test_retry_running_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        tm._save_tasks()

        assert tm.retry_task(task.id) is None


class TestTaskCancellation:
    def test_cancel_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        result = tm.cancel_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED

    def test_cancel_running_task_sets_flag(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        tm._save_tasks()

        result = tm.cancel_task(task.id)
        assert result is not None
        assert result.cancelled is True

    def test_cancel_completed_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.COMPLETED
        tm._save_tasks()

        assert tm.cancel_task(task.id) is None


class TestTaskDeletion:
    def test_delete_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        assert tm.delete_task(task.id) is True
        assert tm.get_task(task.id) is None

    def test_delete_running_task_returns_false(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        tm._save_tasks()

        assert tm.delete_task(task.id) is False
        assert tm.get_task(task.id) is not None

    def test_delete_nonexistent_task(self, task_manager_isolated):
        assert task_manager_isolated.delete_task("fake-id") is False

    def test_delete_completed_tasks(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = tm.create_task(TaskCreate(job_description="JD1"))
        t2 = tm.create_task(TaskCreate(job_description="JD2"))
        t3 = tm.create_task(TaskCreate(job_description="JD3"))
        t1.status = TaskStatus.COMPLETED
        t2.status = TaskStatus.FAILED
        t3.status = TaskStatus.PENDING
        tm._save_tasks()

        count = tm.delete_completed_tasks()
        assert count == 2
        assert tm.get_task(t3.id) is not None


class TestTaskUpdate:
    def test_update_job_description(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        result = tm.update_task_job_description(task.id, "Updated JD")
        assert result is not None
        assert result.job_description == "Updated JD"

    def test_update_settings(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        result = tm.update_task_settings(
            task.id,
            template_id="modern",
            language="zh",
            provider="claude",
        )
        assert result.template_id == "modern"
        assert result.language == "zh"
        assert result.provider == "claude"

    def test_update_running_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        tm._save_tasks()

        assert tm.update_task_job_description(task.id, "New JD") is None
