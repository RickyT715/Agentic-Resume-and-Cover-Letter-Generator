"""Tests for TaskManager question CRUD and answer generation."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.task import QuestionStatus, TaskCreate


class TestAddQuestion:
    def test_add_to_existing_task(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="Test JD"))
        q = tm.add_question(task.id, "Why here?")
        assert q is not None
        assert q.question == "Why here?"
        assert q.word_limit == 150
        assert q.status == QuestionStatus.PENDING

    def test_add_with_custom_word_limit(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Q", word_limit=300)
        assert q.word_limit == 300

    def test_add_returns_none_for_missing_task(self, task_manager_isolated):
        result = task_manager_isolated.add_question("nonexistent", "Q")
        assert result is None

    def test_add_multiple_questions(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        tm.add_question(task.id, "Q1")
        tm.add_question(task.id, "Q2")
        tm.add_question(task.id, "Q3")
        updated_task = tm.get_task(task.id)
        assert len(updated_task.questions) == 3

    def test_question_persisted(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Persisted?")
        # Verify it's on the task
        refreshed = tm.get_task(task.id)
        assert any(qq.id == q.id for qq in refreshed.questions)


class TestUpdateQuestion:
    def test_update_text(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Original")
        updated = tm.update_question(task.id, q.id, question="Updated")
        assert updated.question == "Updated"

    def test_update_text_resets_answer(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Q")
        # Simulate a completed answer
        q.answer = "Some answer"
        q.status = QuestionStatus.COMPLETED
        # Now update question text
        updated = tm.update_question(task.id, q.id, question="Different Q")
        assert updated.answer is None
        assert updated.status == QuestionStatus.PENDING

    def test_update_word_limit_keeps_answer(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Q")
        q.answer = "Answer"
        q.status = QuestionStatus.COMPLETED
        updated = tm.update_question(task.id, q.id, word_limit=200)
        assert updated.word_limit == 200
        assert updated.answer == "Answer"  # not reset

    def test_update_same_text_keeps_answer(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Same Q")
        q.answer = "Answer"
        q.status = QuestionStatus.COMPLETED
        updated = tm.update_question(task.id, q.id, question="Same Q")
        assert updated.answer == "Answer"

    def test_update_nonexistent_task(self, task_manager_isolated):
        result = task_manager_isolated.update_question("nope", "nope", question="Q")
        assert result is None

    def test_update_nonexistent_question(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        result = tm.update_question(task.id, "nope", question="Q")
        assert result is None


class TestDeleteQuestion:
    def test_delete_existing(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Delete me")
        assert tm.delete_question(task.id, q.id) is True
        assert len(tm.get_task(task.id).questions) == 0

    def test_delete_nonexistent_question(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        assert tm.delete_question(task.id, "nope") is False

    def test_delete_nonexistent_task(self, task_manager_isolated):
        assert task_manager_isolated.delete_question("nope", "nope") is False

    def test_delete_preserves_other_questions(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        q1 = tm.add_question(task.id, "Q1")
        q2 = tm.add_question(task.id, "Q2")
        tm.delete_question(task.id, q1.id)
        remaining = tm.get_task(task.id).questions
        assert len(remaining) == 1
        assert remaining[0].id == q2.id


@pytest.mark.asyncio
class TestGenerateQuestionAnswer:
    async def test_successful_generation(self, task_manager_isolated):
        tm = task_manager_isolated
        tm.gemini_client.generate_question_answer = AsyncMock(return_value="  Generated answer.  ")
        task = tm.create_task(TaskCreate(job_description="Software Engineer at Acme"))
        q = tm.add_question(task.id, "Why here?")

        result = await tm.generate_question_answer(task.id, q.id)
        assert result.answer == "Generated answer."
        assert result.status == QuestionStatus.COMPLETED
        assert result.answered_at is not None

    async def test_generation_failure(self, task_manager_isolated):
        tm = task_manager_isolated
        tm.gemini_client.generate_question_answer = AsyncMock(side_effect=Exception("API error"))
        task = tm.create_task(TaskCreate(job_description="JD"))
        q = tm.add_question(task.id, "Q")

        result = await tm.generate_question_answer(task.id, q.id)
        assert result.status == QuestionStatus.FAILED
        assert "API error" in result.error_message

    async def test_nonexistent_task(self, task_manager_isolated):
        result = await task_manager_isolated.generate_question_answer("nope", "nope")
        assert result is None

    async def test_nonexistent_question(self, task_manager_isolated):
        tm = task_manager_isolated
        task = tm.create_task(TaskCreate(job_description="JD"))
        result = await tm.generate_question_answer(task.id, "nope")
        assert result is None

    async def test_prompt_includes_question_text(self, task_manager_isolated):
        tm = task_manager_isolated
        tm.gemini_client.generate_question_answer = AsyncMock(return_value="Answer")
        task = tm.create_task(TaskCreate(job_description="JD at company"))
        q = tm.add_question(task.id, "Why do you want this role?", word_limit=200)

        await tm.generate_question_answer(task.id, q.id)

        # Verify the prompt was built with correct substitutions
        call_args = tm.gemini_client.generate_question_answer.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1]["prompt"]
        assert "Why do you want this role?" in prompt
        assert "JD at company" in prompt
        assert "200" in prompt
