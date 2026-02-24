from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class QuestionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApplicationQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    word_limit: int = 150
    answer: Optional[str] = None
    status: QuestionStatus = QuestionStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    answered_at: Optional[datetime] = None


class TaskStep(str, Enum):
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
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_number: int
    job_description: str
    status: TaskStatus = TaskStatus.PENDING
    generate_cover_letter: bool = True
    template_id: str = "classic"
    language: str = "en"
    provider: Optional[str] = None
    steps: List[StepProgress] = Field(default_factory=list)
    resume_pdf_path: Optional[str] = None
    cover_letter_pdf_path: Optional[str] = None
    latex_source: Optional[str] = None
    error_message: Optional[str] = None
    cancelled: bool = False
    questions: List[ApplicationQuestion] = Field(default_factory=list)
    company_name: str = ""
    position_name: str = ""
    failed_latex_attempts: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def model_post_init(self, __context):
        if not self.steps:
            self._rebuild_steps()

    def _rebuild_steps(self):
        self.steps = [
            StepProgress(step=TaskStep.GENERATE_RESUME),
            StepProgress(step=TaskStep.COMPILE_LATEX),
        ]
        if self.generate_cover_letter:
            self.steps.extend([
                StepProgress(step=TaskStep.EXTRACT_TEXT),
                StepProgress(step=TaskStep.GENERATE_COVER_LETTER),
                StepProgress(step=TaskStep.CREATE_COVER_PDF),
            ])


class TaskCreate(BaseModel):
    job_description: str = ""
    generate_cover_letter: bool = True
    template_id: str = "classic"
    language: str = "en"
    provider: Optional[str] = None


class TaskUpdate(BaseModel):
    job_description: Optional[str] = None
    generate_cover_letter: Optional[bool] = None
    template_id: Optional[str] = None
    language: Optional[str] = None
    provider: Optional[str] = None


class TaskProgressUpdate(BaseModel):
    task_id: str
    step: TaskStep
    status: TaskStatus
    message: str = ""
    attempt: int = 0
