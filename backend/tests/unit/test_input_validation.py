"""Unit tests for Pydantic model field length constraints."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.task import ApplicationQuestion, TaskCreate


class TestTaskCreateValidation:
    def test_job_description_at_max_length_ok(self):
        """job_description of exactly 50000 chars should be accepted."""
        tc = TaskCreate(job_description="x" * 50_000)
        assert len(tc.job_description) == 50_000

    def test_job_description_exceeds_max_length_rejected(self):
        """job_description exceeding 50000 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            TaskCreate(job_description="x" * 50_001)

    def test_company_name_at_max_length_ok(self):
        """company_name of exactly 500 chars is accepted (via Task model only)."""
        # TaskCreate does not have company_name; test through Task model directly
        from models.task import Task

        task = Task(task_number=1, job_description="JD", company_name="A" * 500)
        assert len(task.company_name) == 500

    def test_company_name_exceeds_max_length_rejected(self):
        """company_name exceeding 500 chars should raise ValidationError."""
        from models.task import Task

        with pytest.raises(ValidationError):
            Task(task_number=1, job_description="JD", company_name="A" * 501)

    def test_normal_task_create_ok(self):
        """Normal TaskCreate input is accepted without error."""
        tc = TaskCreate(job_description="Software Engineer at Google")
        assert tc.job_description == "Software Engineer at Google"

    def test_empty_job_description_ok(self):
        """Empty job_description is valid (it is allowed by the model)."""
        tc = TaskCreate(job_description="")
        assert tc.job_description == ""


class TestApplicationQuestionValidation:
    def test_question_at_max_length_ok(self):
        """question of exactly 1000 chars should be accepted."""
        aq = ApplicationQuestion(question="q" * 1_000)
        assert len(aq.question) == 1_000

    def test_question_exceeds_max_length_rejected(self):
        """question exceeding 1000 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            ApplicationQuestion(question="q" * 1_001)

    def test_answer_at_max_length_ok(self):
        """answer of exactly 5000 chars should be accepted."""
        aq = ApplicationQuestion(question="What is your experience?", answer="a" * 5_000)
        assert len(aq.answer) == 5_000

    def test_answer_exceeds_max_length_rejected(self):
        """answer exceeding 5000 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            ApplicationQuestion(question="What is your experience?", answer="a" * 5_001)

    def test_normal_application_question_ok(self):
        """Normal ApplicationQuestion with short question and answer is accepted."""
        aq = ApplicationQuestion(question="Tell me about yourself.", answer="I am a software engineer.")
        assert aq.question == "Tell me about yourself."
        assert aq.answer == "I am a software engineer."

    def test_answer_none_ok(self):
        """answer=None (default) is valid."""
        aq = ApplicationQuestion(question="Why do you want this job?")
        assert aq.answer is None
