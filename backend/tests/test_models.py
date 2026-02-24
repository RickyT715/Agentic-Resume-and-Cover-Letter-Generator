"""Tests for ApplicationQuestion model and Task.questions field."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.task import ApplicationQuestion, QuestionStatus, Task


class TestApplicationQuestion:
    def test_defaults(self):
        q = ApplicationQuestion(question="Why do you want to work here?")
        assert q.question == "Why do you want to work here?"
        assert q.word_limit == 150
        assert q.answer is None
        assert q.status == QuestionStatus.PENDING
        assert q.error_message is None
        assert q.answered_at is None
        assert len(q.id) == 8
        assert q.created_at is not None

    def test_custom_word_limit(self):
        q = ApplicationQuestion(question="Tell me about yourself", word_limit=300)
        assert q.word_limit == 300

    def test_unique_ids(self):
        q1 = ApplicationQuestion(question="Q1")
        q2 = ApplicationQuestion(question="Q2")
        assert q1.id != q2.id

    def test_status_values(self):
        assert QuestionStatus.PENDING == "pending"
        assert QuestionStatus.RUNNING == "running"
        assert QuestionStatus.COMPLETED == "completed"
        assert QuestionStatus.FAILED == "failed"

    def test_serialization_roundtrip(self):
        q = ApplicationQuestion(question="Test?", word_limit=200)
        data = q.model_dump(mode="json")
        restored = ApplicationQuestion(**data)
        assert restored.question == q.question
        assert restored.word_limit == q.word_limit
        assert restored.id == q.id
        assert restored.status == q.status


class TestTaskQuestionsField:
    def test_default_empty_questions(self):
        task = Task(task_number=1, job_description="Test JD")
        assert task.questions == []

    def test_backward_compatibility_no_questions_key(self):
        """Tasks saved before this feature (no questions key) should load fine."""
        data = {
            "id": "abc12345",
            "task_number": 1,
            "job_description": "Old task",
            "status": "completed",
        }
        task = Task(**data)
        assert task.questions == []

    def test_task_with_questions(self):
        q = ApplicationQuestion(question="Why here?")
        task = Task(task_number=1, job_description="JD", questions=[q])
        assert len(task.questions) == 1
        assert task.questions[0].question == "Why here?"

    def test_task_serialization_with_questions(self):
        q = ApplicationQuestion(question="Q1", word_limit=100)
        task = Task(task_number=1, job_description="JD", questions=[q])
        data = task.model_dump(mode="json")
        restored = Task(**data)
        assert len(restored.questions) == 1
        assert restored.questions[0].question == "Q1"
        assert restored.questions[0].word_limit == 100
