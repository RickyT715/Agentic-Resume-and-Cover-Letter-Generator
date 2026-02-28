"""Pydantic schemas for structured AI outputs in the pipeline."""

from pydantic import BaseModel, Field


class JDAnalysis(BaseModel):
    """Structured output from the JD Analyzer agent."""

    job_title: str = Field(description="The job title from the posting")
    company_name: str = Field(default="", description="Company name if mentioned")
    required_skills: list[str] = Field(default_factory=list, description="Required technical and soft skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    experience_level: str = Field(default="", description="Required experience level (e.g., '3-5 years', 'senior')")
    key_responsibilities: list[str] = Field(default_factory=list, description="Main job responsibilities")
    industry: str = Field(default="", description="Industry sector")


class RelevanceMatch(BaseModel):
    """Structured output from the Relevance Matcher agent."""

    matched_skills: list[str] = Field(default_factory=list, description="Skills the candidate has that match the JD")
    missing_skills: list[str] = Field(default_factory=list, description="JD skills the candidate lacks")
    relevant_experiences: list[str] = Field(
        default_factory=list, description="Candidate experiences most relevant to this role"
    )
    emphasis_points: list[str] = Field(
        default_factory=list, description="Points to emphasize in the resume for this specific role"
    )
    match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall match score 0-1")


class QualityEvaluation(BaseModel):
    """Structured output from the Quality Gate evaluation."""

    overall_score: float = Field(ge=0.0, le=1.0, description="Combined quality score 0-1")
    keyword_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Keyword alignment score (TF-IDF)")
    format_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Format and structure score")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Content relevance score")
    feedback: str = Field(default="", description="Actionable improvement feedback")
    passed: bool = Field(default=False, description="Whether the resume passes the quality threshold")
