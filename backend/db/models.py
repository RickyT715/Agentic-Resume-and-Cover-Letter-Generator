"""SQLAlchemy ORM models for the resume generator."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin


class Profile(TimestampMixin, Base):
    """User profile containing personal information for resume generation."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    generation_tasks: Mapped[list["GenerationTask"]] = relationship(back_populates="profile")


class GenerationTask(TimestampMixin, Base):
    """A resume/cover letter generation task."""

    __tablename__ = "generation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_number: Mapped[int] = mapped_column(Integer, nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    pipeline_version: Mapped[str] = mapped_column(String(10), default="v2")

    # Task configuration
    generate_cover_letter: Mapped[bool] = mapped_column(Boolean, default=True)
    template_id: Mapped[str] = mapped_column(String(50), default="classic")
    language: Mapped[str] = mapped_column(String(10), default="en")
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Results
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latex_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)

    # Relationships
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="generation_tasks")
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="task")
    llm_metadata: Mapped[list["LLMGenerationMetadata"]] = relationship(back_populates="task")


class ResumeVersion(TimestampMixin, Base):
    """Versioned resume output, tracking iterations and quality scores."""

    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generation_tasks.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Content
    latex_source: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Evaluation scores (Phase 2)
    evaluation_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    combined_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Self-critique feedback
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task: Mapped["GenerationTask"] = relationship(back_populates="resume_versions")


class LLMGenerationMetadata(TimestampMixin, Base):
    """Metadata for each LLM call within a generation pipeline."""

    __tablename__ = "llm_generation_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generation_tasks.id"), nullable=False)

    # Agent/Node identification
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Provider details
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Token usage
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cost & timing
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # I/O
    prompt_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task: Mapped["GenerationTask"] = relationship(back_populates="llm_metadata")
