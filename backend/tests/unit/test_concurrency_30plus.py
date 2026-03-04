"""Comprehensive concurrency tests for 30+ simultaneous tasks.

Tests cover:
- Task creation at scale (50 concurrent)
- Semaphore capacity validation
- Debounced save mechanism
- Progress notification under load
- Race condition detection
- Cancellation under concurrency
- Task counter integrity
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def concurrent_task_manager(tmp_path):
    """TaskManager configured for high-concurrency testing (50 slots)."""
    from services.prompt_manager import PromptManager
    from services.task_manager import TaskManager

    TaskManager._instance = None

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for fname in [
        "Resume_prompts.txt",
        "Cover_letter_prompt.txt",
        "User_information_prompts.txt",
        "Resume_format_prompts.txt",
        "Application_question_prompt.txt",
        "Resume_prompts_zh.txt",
        "Cover_letter_prompt_zh.txt",
        "User_information_prompts_zh.txt",
        "Resume_format_prompts_zh.txt",
        "Application_question_prompt_zh.txt",
    ]:
        (prompts_dir / fname).write_text("placeholder", encoding="utf-8")

    pm = PromptManager(prompts_dir=prompts_dir)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        patch("services.task_manager.TASKS_FILE", data_dir / "tasks.json"),
        patch("services.task_manager.JD_HISTORY_FILE", data_dir / "jd_history.json"),
        patch("services.task_manager.settings") as mock_settings,
    ):
        mock_settings.data_dir = data_dir
        mock_settings.output_dir = output_dir
        mock_settings.max_concurrent_tasks = 50
        mock_settings.max_latex_retries = 3

        tm = TaskManager.__new__(TaskManager)
        tm._initialized = False
        TaskManager._instance = tm

        tm._initialized = True
        tm.tasks = {}
        tm.task_counter = 0
        tm._progress_callbacks = []
        tm._semaphore = asyncio.Semaphore(50)
        tm._lock = asyncio.Lock()
        tm._last_progress_save = 0.0
        tm._save_interval = 2.0
        tm._deferred_save_handle = None
        tm.settings_manager = MagicMock()
        tm.settings_manager.get.return_value = True
        tm.prompt_manager = pm
        tm.pdf_extractor = MagicMock()
        tm.text_to_pdf = MagicMock()

        tasks_file = data_dir / "tasks.json"

        async def patched_save():
            data = {
                "task_counter": tm.task_counter,
                "tasks": [t.model_dump(mode="json") for t in tm.tasks.values()],
            }
            tasks_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        tm._save_tasks = patched_save

        yield tm

        TaskManager._instance = None


# ======================== Task Creation at Scale ========================


class TestConcurrentTaskCreation:
    """Tests for creating many tasks simultaneously."""

    @pytest.mark.asyncio
    async def test_create_50_tasks_concurrently(self, concurrent_task_manager):
        """50 tasks created concurrently should all succeed with unique IDs."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        async def create(i):
            return await tm.create_task(TaskCreate(job_description=f"Job {i}"))

        tasks = await asyncio.gather(*[create(i) for i in range(50)])

        assert len(tasks) == 50
        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids)), "All task IDs must be unique"

    @pytest.mark.asyncio
    async def test_create_50_tasks_sequential_numbers(self, concurrent_task_manager):
        """50 concurrent tasks should get sequential task numbers 1-50."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])
        numbers = sorted(t.task_number for t in tasks)
        assert numbers == list(range(1, 51))

    @pytest.mark.asyncio
    async def test_task_counter_integrity_under_load(self, concurrent_task_manager):
        """Task counter should equal 50 after 50 concurrent creates."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])
        assert tm.task_counter == 50

    @pytest.mark.asyncio
    async def test_all_tasks_retrievable_after_concurrent_creation(self, concurrent_task_manager):
        """All 50 tasks should be retrievable via get_all_tasks."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        created = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])
        all_tasks = tm.get_all_tasks()
        assert len(all_tasks) == 50
        created_ids = {t.id for t in created}
        retrieved_ids = {t.id for t in all_tasks}
        assert created_ids == retrieved_ids


# ======================== Semaphore Capacity ========================


class TestSemaphoreCapacity:
    """Tests for semaphore allowing 50 concurrent executions."""

    @pytest.mark.asyncio
    async def test_semaphore_allows_50_concurrent(self, concurrent_task_manager):
        """Semaphore should allow at least 50 concurrent acquisitions."""
        tm = concurrent_task_manager
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def work():
            nonlocal max_concurrent, current_concurrent
            async with tm._semaphore:
                async with lock:
                    current_concurrent += 1
                    max_concurrent = max(max_concurrent, current_concurrent)
                await asyncio.sleep(0.01)
                async with lock:
                    current_concurrent -= 1

        await asyncio.gather(*[work() for _ in range(50)])
        assert max_concurrent == 50

    @pytest.mark.asyncio
    async def test_semaphore_limits_to_configured_value(self):
        """A semaphore of 30 should not allow more than 30 concurrent."""
        sem = asyncio.Semaphore(30)
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def work():
            nonlocal max_concurrent, current
            async with sem:
                async with lock:
                    current += 1
                    max_concurrent = max(max_concurrent, current)
                await asyncio.sleep(0.02)
                async with lock:
                    current -= 1

        await asyncio.gather(*[work() for _ in range(60)])
        assert max_concurrent == 30


# ======================== Debounced Save ========================


class TestDebouncedSave:
    """Tests for the debounced _save_tasks mechanism in _notify_progress."""

    @pytest.mark.asyncio
    async def test_terminal_status_always_saves(self, concurrent_task_manager):
        """Terminal statuses (COMPLETED/FAILED) should always trigger a save."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        save_count = 0
        original_save = tm._save_tasks

        async def counting_save():
            nonlocal save_count
            save_count += 1
            await original_save()

        tm._save_tasks = counting_save

        task = await tm.create_task(TaskCreate(job_description="Test"))
        save_count = 0  # Reset after create

        # Set last save to now so throttle is active
        tm._last_progress_save = time.monotonic()

        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.COMPLETED, "Done")
        assert save_count >= 1, "Terminal status must always save"

    @pytest.mark.asyncio
    async def test_rapid_progress_updates_are_throttled(self, concurrent_task_manager):
        """Rapid non-terminal progress updates should be throttled."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        save_count = 0
        original_save = tm._save_tasks

        async def counting_save():
            nonlocal save_count
            save_count += 1
            await original_save()

        tm._save_tasks = counting_save
        tm._save_interval = 10.0  # Very long interval to ensure throttling

        task = await tm.create_task(TaskCreate(job_description="Test"))
        save_count = 0

        # First progress update after interval should save
        tm._last_progress_save = 0.0
        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, "Generating...")
        first_save_count = save_count

        # Subsequent rapid updates within interval should NOT save
        for i in range(10):
            await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, f"Progress {i}")

        # Only the first one should have saved (others throttled)
        assert save_count == first_save_count, "Rapid updates within interval should be throttled"

    @pytest.mark.asyncio
    async def test_deferred_save_scheduled_on_throttle(self, concurrent_task_manager):
        """When a save is throttled, a deferred save should be scheduled."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        tm._save_interval = 100.0  # Ensure throttling

        task = await tm.create_task(TaskCreate(job_description="Test"))
        tm._last_progress_save = time.monotonic()  # Just saved

        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, "Working...")
        assert tm._deferred_save_handle is not None, "Deferred save should be scheduled"

        # Clean up
        tm._deferred_save_handle.cancel()
        tm._deferred_save_handle = None

    @pytest.mark.asyncio
    async def test_deferred_save_cancelled_on_immediate_save(self, concurrent_task_manager):
        """An immediate save should cancel any pending deferred save."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        tm._save_interval = 100.0

        task = await tm.create_task(TaskCreate(job_description="Test"))
        tm._last_progress_save = time.monotonic()

        # Trigger throttled save to schedule deferred
        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, "Working...")
        assert tm._deferred_save_handle is not None

        # Terminal save should cancel the deferred
        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.COMPLETED, "Done")
        assert tm._deferred_save_handle is None, "Deferred save should be cancelled after immediate save"


# ======================== Progress Notifications Under Load ========================


class TestProgressUnderLoad:
    """Tests for progress callbacks working correctly with many concurrent tasks."""

    @pytest.mark.asyncio
    async def test_50_tasks_all_receive_progress_callbacks(self, concurrent_task_manager):
        """All 50 tasks should have their progress callbacks invoked."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        received_updates = []

        async def track_progress(update):
            received_updates.append(update)

        tm._progress_callbacks.append(track_progress)

        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])

        # Send a progress update for each task
        await asyncio.gather(
            *[
                tm._notify_progress(t, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, f"Task {t.task_number}")
                for t in tasks
            ]
        )

        task_ids_notified = {u["task_id"] for u in received_updates}
        task_ids_created = {t.id for t in tasks}
        assert task_ids_created == task_ids_notified

    @pytest.mark.asyncio
    async def test_callback_failure_does_not_block_others(self, concurrent_task_manager):
        """A failing callback should not prevent other callbacks from executing."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        good_results = []

        async def failing_callback(update):
            raise RuntimeError("Callback failed!")

        async def good_callback(update):
            good_results.append(update)

        tm._progress_callbacks.append(failing_callback)
        tm._progress_callbacks.append(good_callback)

        task = await tm.create_task(TaskCreate(job_description="Test"))
        await tm._notify_progress(task, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, "Test")

        assert len(good_results) == 1, "Good callback should still execute after failing one"


# ======================== Race Condition Detection ========================


class TestRaceConditions:
    """Tests to detect race conditions in concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_create_and_delete(self, concurrent_task_manager):
        """Creating and deleting tasks concurrently should not corrupt state."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        # Create 30 tasks first
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(30)])

        # Delete half while creating more
        async def delete_batch():
            for t in tasks[:15]:
                await tm.delete_task(t.id)

        async def create_batch():
            return await asyncio.gather(
                *[tm.create_task(TaskCreate(job_description=f"New job {i}")) for i in range(15)]
            )

        await asyncio.gather(delete_batch(), create_batch())

        # Should have 15 original + 15 new = 30 tasks
        all_tasks = tm.get_all_tasks()
        assert len(all_tasks) == 30

        # Verify no duplicate IDs
        ids = [t.id for t in all_tasks]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_concurrent_create_and_cancel(self, concurrent_task_manager):
        """Cancelling tasks while creating new ones should be safe."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(20)])

        # Cancel first 10 while creating 10 more
        async def cancel_batch():
            for t in tasks[:10]:
                await tm.cancel_task(t.id)

        async def create_more():
            return await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"More {i}")) for i in range(10)])

        await asyncio.gather(cancel_batch(), create_more())

        # All tasks should still be in the dict
        assert len(tm.tasks) == 30

    @pytest.mark.asyncio
    async def test_concurrent_retry_operations(self, concurrent_task_manager):
        """Multiple retry operations should not corrupt task state."""
        from models.task import TaskCreate, TaskStatus

        tm = concurrent_task_manager
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(10)])

        # Set all to failed
        for t in tasks:
            t.status = TaskStatus.FAILED
            t.error_message = "Test failure"

        # Retry all concurrently
        results = await asyncio.gather(*[tm.retry_task(t.id) for t in tasks])

        for result in results:
            assert result is not None
            assert result.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_task_dict_consistency_after_concurrent_ops(self, concurrent_task_manager):
        """After mixed concurrent operations, tasks dict should be consistent."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        # Phase 1: Create 40 tasks
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(40)])

        # Phase 2: Delete 10, create 10 more
        delete_ids = [t.id for t in tasks[:10]]
        ops = []
        for did in delete_ids:
            ops.append(tm.delete_task(did))
        for i in range(10):
            ops.append(tm.create_task(TaskCreate(job_description=f"Extra {i}")))
        await asyncio.gather(*ops)

        # Verify consistency
        all_tasks = tm.get_all_tasks()
        for t in all_tasks:
            assert t.id in tm.tasks
            assert tm.get_task(t.id) is t


# ======================== Concurrent Cancellation ========================


class TestConcurrentCancellation:
    """Tests for cancelling tasks under concurrent load."""

    @pytest.mark.asyncio
    async def test_cancel_30_tasks_simultaneously(self, concurrent_task_manager):
        """Cancelling 30 tasks at once should work correctly."""
        from models.task import TaskCreate, TaskStatus

        tm = concurrent_task_manager
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(30)])

        results = await asyncio.gather(*[tm.cancel_task(t.id) for t in tasks])

        for result in results:
            assert result is not None
            assert result.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_double_cancel_is_safe(self, concurrent_task_manager):
        """Cancelling an already-cancelled task should return None (no error)."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        task = await tm.create_task(TaskCreate(job_description="Test"))
        await tm.cancel_task(task.id)

        # Second cancel should safely return None
        result = await tm.cancel_task(task.id)
        assert result is None


# ======================== Persistence Under Load ========================


class TestPersistenceUnderLoad:
    """Tests for JSON persistence with many tasks."""

    @pytest.mark.asyncio
    async def test_50_tasks_persist_correctly(self, concurrent_task_manager, tmp_path):
        """50 tasks should all be written correctly to the JSON file."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])

        # Force a save
        await tm._save_tasks()

        # Read back and verify
        tasks_file = tmp_path / "data" / "tasks.json"
        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        assert data["task_counter"] == 50
        assert len(data["tasks"]) == 50

        saved_ids = {t["id"] for t in data["tasks"]}
        created_ids = {t.id for t in tasks}
        assert saved_ids == created_ids

    @pytest.mark.asyncio
    async def test_concurrent_saves_do_not_corrupt_file(self, concurrent_task_manager, tmp_path):
        """Multiple concurrent _save_tasks calls should not corrupt the file."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        # Create some tasks
        await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(20)])

        # Trigger many concurrent saves
        await asyncio.gather(*[tm._save_tasks() for _ in range(20)])

        # File should still be valid JSON with all 20 tasks
        tasks_file = tmp_path / "data" / "tasks.json"
        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 20


# ======================== Semaphore + Run Task Interaction ========================


class TestSemaphoreRunInteraction:
    """Tests for semaphore behavior during task execution."""

    @pytest.mark.asyncio
    async def test_run_task_acquires_and_releases_semaphore(self, concurrent_task_manager):
        """run_task should acquire semaphore on entry and release on completion."""
        from models.task import TaskCreate, TaskStatus

        tm = concurrent_task_manager

        initial_value = tm._semaphore._value

        task = await tm.create_task(TaskCreate(job_description="Test"))

        # Mock _execute_task to just complete the task
        async def mock_execute(task_id):
            t = tm.get_task(task_id)
            t.status = TaskStatus.COMPLETED

        tm._execute_task = mock_execute

        await tm.run_task(task.id)

        # Semaphore should be back to initial value
        assert tm._semaphore._value == initial_value

    @pytest.mark.asyncio
    async def test_30_tasks_can_run_through_semaphore(self, concurrent_task_manager):
        """30 tasks should all be able to acquire the semaphore (capacity 50)."""
        from models.task import TaskCreate, TaskStatus

        tm = concurrent_task_manager
        completed = []

        async def mock_execute(task_id):
            t = tm.get_task(task_id)
            await asyncio.sleep(0.01)
            t.status = TaskStatus.COMPLETED
            completed.append(task_id)

        tm._execute_task = mock_execute

        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(30)])

        await asyncio.gather(*[tm.run_task(t.id) for t in tasks])

        assert len(completed) == 30


# ======================== Config Validation ========================


class TestConfigDefaults:
    """Tests for config default values supporting 30+ concurrency."""

    def test_max_concurrent_tasks_default_is_50(self):
        """Config should default to 50 concurrent tasks."""
        from config import Settings

        s = Settings()
        assert s.max_concurrent_tasks == 50

    def test_max_concurrent_tasks_env_override(self):
        """max_concurrent_tasks should be overridable via environment."""
        with patch.dict("os.environ", {"MAX_CONCURRENT_TASKS": "100"}):
            from config import Settings

            s = Settings()
            assert s.max_concurrent_tasks == 100


# ======================== Rate Limit Config ========================


class TestRateLimitConfig:
    """Tests for rate limit settings supporting 30+ task creation."""

    def test_task_create_rate_allows_60_per_minute(self):
        """Task creation rate limit should allow at least 60/minute."""
        from middleware.rate_limit import TASK_CREATE_RATE

        # Parse the rate string
        count = int(TASK_CREATE_RATE.split("/")[0])
        assert count >= 60, f"Task create rate {TASK_CREATE_RATE} too low for 30+ concurrent tasks"


# ======================== Stress Test ========================


class TestStress:
    """Higher-load stress tests."""

    @pytest.mark.asyncio
    async def test_create_100_tasks_concurrently(self, concurrent_task_manager):
        """Create 100 tasks concurrently to stress test locking."""
        from models.task import TaskCreate

        tm = concurrent_task_manager
        tasks = await asyncio.gather(
            *[tm.create_task(TaskCreate(job_description=f"Stress job {i}")) for i in range(100)]
        )

        assert len(tasks) == 100
        numbers = sorted(t.task_number for t in tasks)
        assert numbers == list(range(1, 101))
        assert tm.task_counter == 100

    @pytest.mark.asyncio
    async def test_mixed_operations_50_tasks(self, concurrent_task_manager):
        """Run create, read, cancel, delete in parallel across 50 tasks."""
        from models.task import TaskCreate

        tm = concurrent_task_manager

        # Create 50
        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])

        # Mixed operations
        ops = []
        for i, t in enumerate(tasks):
            if i % 3 == 0:
                ops.append(tm.cancel_task(t.id))
            elif i % 3 == 1:
                ops.append(tm.delete_task(t.id))

        await asyncio.gather(*ops)

        # Verify no crashes and state is consistent
        remaining = tm.get_all_tasks()
        for t in remaining:
            assert t.id in tm.tasks

    @pytest.mark.asyncio
    async def test_rapid_progress_updates_50_tasks(self, concurrent_task_manager):
        """50 tasks each sending 5 progress updates concurrently."""
        from models.task import TaskCreate, TaskStatus, TaskStep

        tm = concurrent_task_manager
        tm._save_interval = 0.1  # Short interval for test

        tasks = await asyncio.gather(*[tm.create_task(TaskCreate(job_description=f"Job {i}")) for i in range(50)])

        # Each task sends 5 progress updates
        ops = []
        for t in tasks:
            for j in range(5):
                ops.append(tm._notify_progress(t, TaskStep.GENERATE_RESUME, TaskStatus.RUNNING, f"Step {j}"))

        await asyncio.gather(*ops)

        # No crash = success; verify all tasks still intact
        assert len(tm.tasks) == 50
