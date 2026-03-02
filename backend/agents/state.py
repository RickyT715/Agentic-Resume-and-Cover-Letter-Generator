"""LangGraph state definitions for the resume generation pipeline."""

from typing import Any

from typing_extensions import TypedDict


class ResumeState(TypedDict, total=False):
    """State that flows through the resume generation pipeline.

    Each agent node reads from and writes to this shared state.
    Fields marked total=False are optional and may not be present
    at every stage of the pipeline.
    """

    # ---- Input (set at pipeline start) ----
    task_id: str
    task_number: int
    job_description: str
    language: str
    template_id: str
    generate_cover_letter: bool
    experience_level: str
    provider_name: str

    # ---- User profile ----
    user_information: str

    # ---- JD Analysis (set by jd_analyzer) ----
    jd_analysis: dict[str, Any]
    # Structure: {
    #   "job_title": str,
    #   "company_name": str,
    #   "required_skills": list[str],
    #   "preferred_skills": list[str],
    #   "experience_level": str,
    #   "key_responsibilities": list[str],
    #   "industry": str,
    # }

    # ---- Relevance Matching (set by relevance_matcher) ----
    relevance_match: dict[str, Any]
    # Structure: {
    #   "matched_skills": list[str],
    #   "missing_skills": list[str],
    #   "relevant_experiences": list[str],
    #   "emphasis_points": list[str],
    #   "match_score": float,  # 0-1
    # }

    # ---- Resume Generation (set by resume_writer) ----
    latex_source: str
    resume_prompt: str

    # ---- Quality Gate (set by quality_gate) ----
    quality_score: float
    quality_feedback: str
    quality_passed: bool
    retry_count: int

    # ---- Cover Letter (set by cover_letter_writer) ----
    resume_text: str  # extracted from compiled PDF
    cover_letter_text: str

    # ---- Compilation & Output (set by finalize) ----
    resume_pdf_path: str | None
    cover_letter_pdf_path: str | None
    company_name: str
    position_name: str

    # ---- RAG Context (Phase 4 - optional) ----
    company_context: str | None

    # ---- Metadata ----
    error: str | None
    agent_outputs: dict[str, Any]  # Per-agent metadata (tokens, latency, etc.)
    current_node: str  # For progress tracking
