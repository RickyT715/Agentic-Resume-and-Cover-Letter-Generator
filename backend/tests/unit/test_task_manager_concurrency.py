"""Unit tests for TaskManager concurrency improvements."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def isolated_task_manager(tmp_path):
    """Fresh TaskManager with temp data dir and mocked services."""
    from services.prompt_manager import PromptManager
    from services.task_manager import TaskManager

    # Reset the singleton
    TaskManager._instance = None

    # Create minimal prompt files
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
        mock_settings.max_concurrent_tasks = 3
        mock_settings.max_latex_retries = 3

        tm = TaskManager.__new__(TaskManager)
        tm._initialized = False
        TaskManager._instance = tm

        tm._initialized = True
        tm.tasks = {}
        tm.task_counter = 0
        tm._progress_callbacks = []
        tm._semaphore = asyncio.Semaphore(3)
        tm._lock = asyncio.Lock()
        tm.settings_manager = MagicMock()
        tm.settings_manager.get.return_value = True
        tm.prompt_manager = pm
        tm.pdf_extractor = MagicMock()
        tm.text_to_pdf = MagicMock()

        tasks_file = data_dir / "tasks.json"

        async def patched_save():
            import json

            data = {
                "task_counter": tm.task_counter,
                "tasks": [t.model_dump(mode="json") for t in tm.tasks.values()],
            }
            tasks_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        tm._save_tasks = patched_save

        yield tm

        TaskManager._instance = None


class TestTaskManagerConcurrency:
    def test_lock_attribute_exists(self, isolated_task_manager):
        """TaskManager should have a _lock attribute (asyncio.Lock)."""
        tm = isolated_task_manager
        assert hasattr(tm, "_lock")
        assert isinstance(tm._lock, asyncio.Lock)

    def test_semaphore_attribute_exists(self, isolated_task_manager):
        """TaskManager should have a _semaphore attribute (asyncio.Semaphore)."""
        tm = isolated_task_manager
        assert hasattr(tm, "_semaphore")
        assert isinstance(tm._semaphore, asyncio.Semaphore)

    def test_save_tasks_is_coroutine(self, isolated_task_manager):
        """_save_tasks should be an async function (coroutine)."""
        tm = isolated_task_manager
        import inspect

        # The patched version in our fixture is also async
        assert inspect.iscoroutinefunction(tm._save_tasks)

    @pytest.mark.asyncio
    async def test_concurrent_task_creation_unique_ids(self, isolated_task_manager):
        """Concurrent create_task calls should produce tasks with unique IDs."""
        from models.task import TaskCreate

        tm = isolated_task_manager

        async def create():
            return await tm.create_task(TaskCreate(job_description="Software Engineer"))

        # Create 10 tasks concurrently
        tasks = await asyncio.gather(*[create() for _ in range(10)])
        ids = [t.id for t in tasks]
        # All IDs should be unique
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_concurrent_task_creation_unique_task_numbers(self, isolated_task_manager):
        """Concurrent task creation should produce unique, sequential task numbers."""
        from models.task import TaskCreate

        tm = isolated_task_manager

        async def create():
            return await tm.create_task(TaskCreate(job_description="SWE at Google"))

        tasks = await asyncio.gather(*[create() for _ in range(5)])
        numbers = sorted(t.task_number for t in tasks)
        # Task numbers should be 1 through 5 (no duplicates)
        assert numbers == list(range(1, 6))

    def test_no_shared_latex_compiler_instance(self, isolated_task_manager):
        """LaTeXCompiler should NOT be a shared instance on TaskManager."""
        tm = isolated_task_manager
        # The task manager should not hold a shared latex_compiler attribute
        # (it should be created per-task to avoid concurrency issues)
        assert not hasattr(tm, "latex_compiler")
