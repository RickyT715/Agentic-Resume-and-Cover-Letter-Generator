"""Quality Gate node: evaluates resume quality and decides whether to retry.

Phase 1: Placeholder scoring based on heuristics.
Phase 2: Will integrate ATS scoring + LLM-as-judge.
"""

import logging
import re

from agents.state import ResumeState

logger = logging.getLogger(__name__)

# Quality threshold - below this triggers a retry
QUALITY_THRESHOLD = 0.7
MAX_RETRIES = 2


def _heuristic_score(latex_source: str, jd_analysis: dict) -> tuple[float, str]:
    """Compute a heuristic quality score for a LaTeX resume.

    Returns (score, feedback) where score is 0-1.
    This is a placeholder for Phase 2's full ATS + LLM evaluation.
    """
    score = 0.0
    feedback_items: list[str] = []
    weights = {
        "structure": 0.25,
        "keyword_match": 0.35,
        "length": 0.15,
        "formatting": 0.25,
    }

    # 1. Structure check (25%) - has required LaTeX sections
    sections_found = 0
    expected_sections = ["experience", "education", "skill", "project", "summary"]
    lower_latex = latex_source.lower()
    for section in expected_sections:
        if section in lower_latex:
            sections_found += 1
    structure_score = min(sections_found / 3, 1.0)  # At least 3 of 5
    score += structure_score * weights["structure"]
    if sections_found < 3:
        feedback_items.append(
            f"Resume has only {sections_found} of expected sections (experience, education, skills, etc.)"
        )

    # 2. Keyword match (35%) - JD required skills found in resume
    required_skills = jd_analysis.get("required_skills", [])
    if required_skills:
        matched = sum(1 for skill in required_skills if skill.lower() in lower_latex)
        keyword_score = matched / len(required_skills)
        score += keyword_score * weights["keyword_match"]
        if keyword_score < 0.5:
            missing = [s for s in required_skills if s.lower() not in lower_latex]
            feedback_items.append(f"Missing key skills from JD: {', '.join(missing[:5])}")
    else:
        score += 0.7 * weights["keyword_match"]

    # 3. Length check (15%) - reasonable resume length
    char_count = len(latex_source)
    if 2000 <= char_count <= 8000:
        length_score = 1.0
    elif char_count < 1000:
        length_score = 0.3
        feedback_items.append("Resume is too short - add more detail to experience and projects")
    elif char_count > 10000:
        length_score = 0.5
        feedback_items.append("Resume is too long - condense to fit one page")
    else:
        length_score = 0.7
    score += length_score * weights["length"]

    # 4. Formatting quality (25%) - action verbs, quantified achievements
    action_verbs = [
        "led",
        "developed",
        "implemented",
        "designed",
        "built",
        "managed",
        "increased",
        "reduced",
        "improved",
        "created",
        "launched",
        "optimized",
        "achieved",
        "delivered",
    ]
    verb_count = sum(1 for verb in action_verbs if re.search(rf"\b{verb}\b", lower_latex))
    verb_score = min(verb_count / 5, 1.0)

    # Check for quantified achievements (numbers in bullet points)
    numbers = re.findall(r"\d+[%x+]|\$[\d,]+|\d+\+?\s*(?:users|customers|projects|team)", lower_latex)
    quant_score = min(len(numbers) / 3, 1.0)

    format_score = (verb_score + quant_score) / 2
    score += format_score * weights["formatting"]
    if verb_count < 3:
        feedback_items.append("Use more action verbs (led, developed, implemented, etc.)")
    if len(numbers) < 2:
        feedback_items.append("Add quantified achievements (percentages, numbers, metrics)")

    feedback = "; ".join(feedback_items) if feedback_items else "Resume meets quality standards"
    return round(score, 3), feedback


async def quality_gate_node(state: ResumeState) -> dict:
    """Evaluate resume quality and decide whether to retry.

    Uses the evaluation module (ATS scorer) for deterministic scoring.
    Falls back to heuristic scoring if the evaluation module fails.

    Reads: latex_source, jd_analysis, job_description, retry_count
    Writes: quality_score, quality_feedback, quality_passed, retry_count, current_node
    """
    retry_count = state.get("retry_count", 0)
    latex_source = state.get("latex_source", "")
    jd_analysis = state.get("jd_analysis", {})

    try:
        from evaluation.ats_scorer import score_resume
        from evaluation.feedback_generator import generate_feedback

        ats_result = score_resume(
            latex_source,
            state.get("job_description", ""),
            jd_analysis,
        )
        score = ats_result.overall
        feedback = generate_feedback(ats_result, None, score)
    except Exception as e:
        logger.warning(f"Evaluation module failed, using heuristic: {e}")
        score, feedback = _heuristic_score(latex_source, jd_analysis)

    passed = score >= QUALITY_THRESHOLD or retry_count >= MAX_RETRIES

    logger.info(
        f"Task {state['task_number']}: Quality gate - "
        f"score={score:.2f}, threshold={QUALITY_THRESHOLD}, "
        f"passed={passed}, retries={retry_count}/{MAX_RETRIES}"
    )

    if not passed:
        logger.info(f"Task {state['task_number']}: Quality gate failed, will retry. Feedback: {feedback}")

    return {
        "quality_score": score,
        "quality_feedback": feedback,
        "quality_passed": passed,
        "retry_count": retry_count + (0 if passed else 1),
        "current_node": "quality_gate",
    }


def should_retry(state: ResumeState) -> str:
    """Conditional edge: route to retry or continue based on quality gate.

    Returns:
        "resume_writer" if quality failed and retries remain
        "compile_latex" if quality passed or max retries reached
    """
    if state.get("quality_passed", True):
        return "compile_latex"
    return "resume_writer"
