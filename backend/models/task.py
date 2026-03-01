import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class QuestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApplicationQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    word_limit: int = 150
    answer: str | None = None
    status: QuestionStatus = QuestionStatus.PENDING
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    answered_at: datetime | None = None


class TaskStep(StrEnum):
    GENERATE_RESUME = "generate_resume"
    COMPILE_LATEX = "compile_latex"
    EXTRACT_TEXT = "extract_text"
    GENERATE_COVER_LETTER = "generate_cover_letter"
    CREATE_COVER_PDF = "create_cover_pdf"


class StepProgress(BaseModel):
    step: TaskStep
    status: TaskStatus = TaskStatus.PENDING
    message: str = ""
    attempt: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_number: int
    job_description: str
    status: TaskStatus = TaskStatus.PENDING
    generate_cover_letter: bool = True
    template_id: str = "classic"
    language: str = "en"
    provider: str | None = None
    pipeline_version: str = "v2"
    steps: list[StepProgress] = Field(default_factory=list)
    resume_pdf_path: str | None = None
    cover_letter_pdf_path: str | None = None
    cover_letter_text: str | None = None
    latex_source: str | None = None
    error_message: str | None = None
    cancelled: bool = False
    questions: list[ApplicationQuestion] = Field(default_factory=list)
    company_name: str = ""
    position_name: str = ""
    failed_latex_attempts: list[str] = Field(default_factory=list)
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def model_post_init(self, __context):
        if not self.steps:
            self._rebuild_steps()

    def _rebuild_steps(self):
        self.steps = [
            StepProgress(step=TaskStep.GENERATE_RESUME),
            StepProgress(step=TaskStep.COMPILE_LATEX),
        ]
        if self.generate_cover_letter:
            self.steps.extend(
                [
                    StepProgress(step=TaskStep.EXTRACT_TEXT),
                    StepProgress(step=TaskStep.GENERATE_COVER_LETTER),
                    StepProgress(step=TaskStep.CREATE_COVER_PDF),
                ]
            )


class TaskCreate(BaseModel):
    job_description: str = ""
    generate_cover_letter: bool = True
    template_id: str = "classic"
    language: str = "en"
    provider: str | None = None


class TaskUpdate(BaseModel):
    job_description: str | None = None
    generate_cover_letter: bool | None = None
    template_id: str | None = None
    language: str | None = None
    provider: str | None = None


class TaskProgressUpdate(BaseModel):
    task_id: str
    step: TaskStep
    status: TaskStatus
    message: str = ""
    attempt: int = 0
