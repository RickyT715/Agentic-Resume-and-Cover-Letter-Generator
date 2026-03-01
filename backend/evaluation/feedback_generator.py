"""Feedback generator: converts evaluation scores into actionable improvement prompts."""

import logging

from evaluation.ats_scorer import ATSScoreBreakdown
from evaluation.llm_judge import LLMJudgeResult

logger = logging.getLogger(__name__)


def generate_feedback(
    ats_score: ATSScoreBreakdown,
    llm_judge: LLMJudgeResult | None = None,
    combined_score: float = 0.0,
    language: str = "en",
) -> str:
    """Generate actionable feedback from evaluation results.

    This feedback is appended to the retry prompt when the quality gate
    sends the resume back for improvement.

    Args:
        ats_score: Deterministic ATS scoring results
        llm_judge: Optional LLM-as-judge results
        combined_score: The combined (weighted) score
        language: "en" or "zh" — output language for feedback

    Returns:
        Structured feedback string for the AI to improve the resume
    """
    if language == "zh":
        return _generate_feedback_zh(ats_score, llm_judge, combined_score)

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
    sections.append(f"- Keyword Relevance (BM25): {ats_score.keyword_similarity:.0%}")
    sections.append(f"- Semantic Match: {ats_score.semantic_similarity:.0%}")
    sections.append(f"- Skill Coverage: {ats_score.skill_coverage:.0%}")
    sections.append(f"- Fuzzy Match: {ats_score.fuzzy_match:.0%}")
    sections.append(f"- Resume Quality: {ats_score.resume_quality:.0%}")
    sections.append(f"- Section Placement: {ats_score.section_bonus:.0%}")
    sections.append(f"  - Action Verbs: {ats_score.action_verbs_score:.0%}")
    sections.append(f"  - Quantified Results: {ats_score.quantified_score:.0%}")
    sections.append(f"  - Sections: {ats_score.section_score:.0%}")
    sections.append(f"  - Format: {ats_score.format_score:.0%}")

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


def _generate_feedback_zh(
    ats_score: ATSScoreBreakdown,
    llm_judge: LLMJudgeResult | None = None,
    combined_score: float = 0.0,
) -> str:
    """Generate Chinese feedback for resume improvement."""
    sections: list[str] = []

    sections.append(f"上一次生成得分 {combined_score:.2f}/1.0。")
    sections.append("")

    if ats_score.feedback:
        sections.append("## ATS评估反馈")
        for item in ats_score.feedback:
            sections.append(f"- {item}")
        sections.append("")

    if ats_score.missing_keywords:
        sections.append("## 缺失关键词（请自然地融入简历）")
        for kw in ats_score.missing_keywords[:8]:
            sections.append(f"- {kw}")
        sections.append("")

    sections.append("## 各项评分")
    sections.append(f"- 关键词相关性 (BM25): {ats_score.keyword_similarity:.0%}")
    sections.append(f"- 语义匹配度: {ats_score.semantic_similarity:.0%}")
    sections.append(f"- 技能覆盖率: {ats_score.skill_coverage:.0%}")
    sections.append(f"- 模糊匹配: {ats_score.fuzzy_match:.0%}")
    sections.append(f"- 简历质量: {ats_score.resume_quality:.0%}")
    sections.append(f"- 板块分布: {ats_score.section_bonus:.0%}")
    sections.append(f"  - 动词使用: {ats_score.action_verbs_score:.0%}")
    sections.append(f"  - 量化成果: {ats_score.quantified_score:.0%}")
    sections.append(f"  - 板块完整性: {ats_score.section_score:.0%}")
    sections.append(f"  - 格式规范: {ats_score.format_score:.0%}")

    if llm_judge and llm_judge.improvements:
        sections.append("")
        sections.append("## 专家评审反馈")
        sections.append(llm_judge.reasoning)
        sections.append("")
        sections.append("需要改进的具体方面：")
        for improvement in llm_judge.improvements[:5]:
            sections.append(f"- {improvement}")

    sections.append("")
    sections.append("请根据以上所有反馈重新生成简历。")

    feedback = "\n".join(sections)
    logger.info(f"Generated Chinese feedback ({len(feedback)} chars)")
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
