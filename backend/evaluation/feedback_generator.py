"""Feedback generator: converts evaluation scores into actionable improvement prompts."""

import logging

from evaluation.ats_scorer import ATSScoreBreakdown
from evaluation.llm_judge import LLMJudgeResult

logger = logging.getLogger(__name__)


def generate_feedback(
    ats_score: ATSScoreBreakdown,
    llm_judge: LLMJudgeResult | None = None,
    combined_score: float = 0.0,
) -> str:
    """Generate actionable feedback from evaluation results.

    This feedback is appended to the retry prompt when the quality gate
    sends the resume back for improvement.

    Args:
        ats_score: Deterministic ATS scoring results
        llm_judge: Optional LLM-as-judge results
        combined_score: The combined (weighted) score

    Returns:
        Structured feedback string for the AI to improve the resume
    """
    sections: list[str] = []

    sections.append(f"Previous attempt scored {combined_score:.2f}/1.0.")
    sections.append("")

    # ATS-based feedback
    if ats_score.feedback:
        sections.append("## ATS Evaluation Feedback")
        for item in ats_score.feedback:
            sections.append(f"- {item}")
        sections.append("")

    if ats_score.missing_keywords:
        sections.append("## Missing Keywords (incorporate naturally)")
        for kw in ats_score.missing_keywords[:8]:
            sections.append(f"- {kw}")
        sections.append("")

    # Score breakdown
    sections.append("## Score Breakdown")
    sections.append(f"- Keyword Match: {ats_score.keyword_match:.0%}")
    sections.append(f"- Experience Alignment: {ats_score.experience_alignment:.0%}")
    sections.append(f"- Format Quality: {ats_score.format_score:.0%}")
    sections.append(f"- Action Verbs: {ats_score.action_verbs:.0%}")
    sections.append(f"- Quantified Results: {ats_score.readability:.0%}")
    sections.append(f"- Section Completeness: {ats_score.section_completeness:.0%}")

    # LLM judge feedback
    if llm_judge and llm_judge.improvements:
        sections.append("")
        sections.append("## Expert Reviewer Feedback")
        sections.append(llm_judge.reasoning)
        sections.append("")
        sections.append("Specific improvements needed:")
        for improvement in llm_judge.improvements[:5]:
            sections.append(f"- {improvement}")

    sections.append("")
    sections.append("Please regenerate the resume addressing ALL of the above feedback.")

    feedback = "\n".join(sections)
    logger.info(f"Generated feedback ({len(feedback)} chars)")
    return feedback


def compute_combined_score(
    ats_score: float,
    llm_score: float | None = None,
    ats_weight: float = 0.6,
) -> float:
    """Compute weighted combined score from ATS and LLM evaluations.

    Args:
        ats_score: Deterministic ATS score (0-1)
        llm_score: Optional LLM judge score (0-1)
        ats_weight: Weight for ATS score (default 0.6, LLM gets 1-ats_weight)

    Returns:
        Combined score 0-1
    """
    if llm_score is not None:
        return round(ats_score * ats_weight + llm_score * (1 - ats_weight), 3)
    return round(ats_score, 3)
