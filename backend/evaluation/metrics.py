"""Combined evaluation metrics: runs both ATS and LLM-judge, produces final score."""

import logging

from evaluation.ats_scorer import ATSScoreBreakdown, score_resume
from evaluation.feedback_generator import compute_combined_score, generate_feedback
from evaluation.llm_judge import LLMJudgeResult, evaluate_with_llm

logger = logging.getLogger(__name__)


async def evaluate_resume(
    resume_latex: str,
    job_description: str,
    jd_analysis: dict | None = None,
    provider_name: str = "gemini",
    task_id: str = "",
    task_number: int = 0,
    use_llm_judge: bool = True,
) -> dict:
    """Run full evaluation pipeline on a resume.

    Combines:
    1. Deterministic ATS scoring (always runs)
    2. LLM-as-judge evaluation (optional, adds latency)

    Args:
        resume_latex: LaTeX source of the resume
        job_description: Raw job description text
        jd_analysis: Structured JD analysis (optional)
        provider_name: AI provider for LLM judge
        task_id: For logging/tracking
        task_number: For logging/tracking
        use_llm_judge: Whether to run LLM evaluation (slower but more nuanced)

    Returns:
        Dict with ats_score, llm_score, combined_score, feedback, and full breakdown
    """
    # Always run ATS scoring (deterministic, fast)
    ats_result = score_resume(resume_latex, job_description, jd_analysis)

    # Optionally run LLM judge
    llm_result = None
    if use_llm_judge:
        try:
            llm_result = await evaluate_with_llm(
                resume_latex=resume_latex,
                job_description=job_description,
                provider_name=provider_name,
                task_id=task_id,
                task_number=task_number,
            )
        except Exception as e:
            logger.warning(f"LLM judge failed, using ATS score only: {e}")

    # Compute combined score
    llm_score = llm_result.overall_score if llm_result else None
    combined = compute_combined_score(ats_result.overall, llm_score)

    # Generate feedback
    feedback = generate_feedback(ats_result, llm_result, combined)

    return {
        "ats_score": ats_result.overall,
        "ats_breakdown": {
            "keyword_match": ats_result.keyword_match,
            "experience_alignment": ats_result.experience_alignment,
            "format_score": ats_result.format_score,
            "action_verbs": ats_result.action_verbs,
            "readability": ats_result.readability,
            "section_completeness": ats_result.section_completeness,
        },
        "matched_keywords": ats_result.matched_keywords,
        "missing_keywords": ats_result.missing_keywords,
        "llm_score": llm_score,
        "llm_breakdown": (
            {
                "keyword_alignment": llm_result.keyword_alignment,
                "professional_tone": llm_result.professional_tone,
                "quantified_achievements": llm_result.quantified_achievements,
                "relevance": llm_result.relevance,
                "ats_compliance": llm_result.ats_compliance,
                "reasoning": llm_result.reasoning,
                "improvements": llm_result.improvements,
            }
            if llm_result
            else None
        ),
        "combined_score": combined,
        "feedback": feedback,
        "passed": combined >= 0.7,
    }
