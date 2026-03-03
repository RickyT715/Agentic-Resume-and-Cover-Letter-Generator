"""Integration tests for task state machine transitions."""

import pytest

from models.task import TaskCreate, TaskStatus


@pytest.mark.asyncio
class TestTaskCreation:
    async def test_create_task_increments_counter(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = await tm.create_task(TaskCreate(job_description="JD1"))
        t2 = await tm.create_task(TaskCreate(job_description="JD2"))
        assert t1.task_number == 1
        assert t2.task_number == 2

    async def test_create_task_default_status(self, task_manager_isolated):
        task = await task_manager_isolated.create_task(TaskCreate(job_description="JD"))
        assert task.status == TaskStatus.PENDING

    async def test_create_task_with_cover_letter(self, task_manager_isolated):
        task = await task_manager_isolated.create_task(TaskCreate(job_description="JD", generate_cover_letter=True))
        assert task.generate_cover_letter is True
        assert len(task.steps) == 5

    async def test_create_task_without_cover_letter(self, task_manager_isolated):
        task = await task_manager_isolated.create_task(TaskCreate(job_description="JD", generate_cover_letter=False))
        assert task.generate_cover_letter is False
        assert len(task.steps) == 2


@pytest.mark.asyncio
class TestTaskRetry:
    async def test_retry_failed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.FAILED
        await tm._save_tasks()

        retried = await tm.retry_task(task.id)
        assert retried is not None
        assert retried.status == TaskStatus.PENDING
        assert retried.error_message is None

    async def test_retry_completed_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.COMPLETED
        await tm._save_tasks()

        retried = await tm.retry_task(task.id)
        assert retried is not None
        assert retried.status == TaskStatus.PENDING

    async def test_retry_running_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        await tm._save_tasks()

        assert await tm.retry_task(task.id) is None


@pytest.mark.asyncio
class TestTaskCancellation:
    async def test_cancel_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.cancel_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED

    async def test_cancel_running_task_sets_flag(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        await tm._save_tasks()

        result = await tm.cancel_task(task.id)
        assert result is not None
        assert result.cancelled is True

    async def test_cancel_completed_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.COMPLETED
        await tm._save_tasks()

        assert await tm.cancel_task(task.id) is None


@pytest.mark.asyncio
class TestTaskDeletion:
    async def test_delete_pending_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        assert await tm.delete_task(task.id) is True
        assert tm.get_task(task.id) is None

    async def test_delete_running_task_returns_false(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        await tm._save_tasks()

        assert await tm.delete_task(task.id) is False
        assert tm.get_task(task.id) is not None

    async def test_delete_nonexistent_task(self, task_manager_isolated):
        assert await task_manager_isolated.delete_task("fake-id") is False

    async def test_delete_completed_tasks(self, task_manager_isolated):
        tm = task_manager_isolated
        t1 = await tm.create_task(TaskCreate(job_description="JD1"))
        t2 = await tm.create_task(TaskCreate(job_description="JD2"))
        t3 = await tm.create_task(TaskCreate(job_description="JD3"))
        t1.status = TaskStatus.COMPLETED
        t2.status = TaskStatus.FAILED
        t3.status = TaskStatus.PENDING
        await tm._save_tasks()

        count = await tm.delete_completed_tasks()
        assert count == 2
        assert tm.get_task(t3.id) is not None


@pytest.mark.asyncio
class TestTaskUpdate:
    async def test_update_job_description(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.update_task_job_description(task.id, "Updated JD")
        assert result is not None
        assert result.job_description == "Updated JD"

    async def test_update_settings(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.update_task_settings(
            task.id,
            template_id="modern",
            language="zh",
            provider="claude",
        )
        assert result.template_id == "modern"
        assert result.language == "zh"
        assert result.provider == "claude"

    async def test_update_running_task_returns_none(self, task_manager_isolated):
        tm = task_manager_isolated
        task = await tm.create_task(TaskCreate(job_description="JD"))
        task.status = TaskStatus.RUNNING
        await tm._save_tasks()

        assert await tm.update_task_job_description(task.id, "New JD") is None
