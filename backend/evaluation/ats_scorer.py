"""Deterministic ATS (Applicant Tracking System) scoring.

Uses NLP techniques to score resume-JD alignment:
- Keyword extraction and matching (TF-IDF cosine similarity)
- Action verb detection
- Quantified achievement detection
- Section completeness
- Readability heuristics
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

ACTION_VERBS = [
    "achieved", "built", "created", "delivered", "designed", "developed",
    "engineered", "established", "implemented", "improved", "increased",
    "launched", "led", "managed", "optimized", "orchestrated", "pioneered",
    "reduced", "refactored", "scaled", "spearheaded", "streamlined",
    "transformed", "architected", "automated", "collaborated", "contributed",
    "deployed", "drove", "executed", "facilitated", "generated", "initiated",
    "integrated", "maintained", "mentored", "migrated", "modernized",
    "resolved", "restructured", "secured", "shipped", "standardized",
]

EXPECTED_SECTIONS = ["experience", "education", "skill", "project", "summary", "objective"]


@dataclass
class ATSScoreBreakdown:
    """Detailed ATS score breakdown."""

    keyword_match: float = 0.0
    experience_alignment: float = 0.0
    format_score: float = 0.0
    action_verbs: float = 0.0
    readability: float = 0.0
    section_completeness: float = 0.0
    overall: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)


def _extract_text_from_latex(latex: str) -> str:
    """Strip LaTeX commands to get plain text for analysis."""
    text = latex
    # Remove common LaTeX commands
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[.*?\])?\{([^}]*)\}", r"\2", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}\\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords (2+ letter words, excluding common stop words)."""
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
        "was", "one", "our", "out", "has", "had", "his", "how", "its", "let",
        "may", "new", "now", "old", "see", "way", "who", "did", "get", "got",
        "him", "use", "say", "she", "too", "than", "that", "this", "with",
        "will", "each", "make", "like", "from", "just", "over", "such", "take",
        "into", "very", "have", "been", "well", "then", "some", "them", "when",
        "what", "where", "which", "while", "work", "year", "also", "more",
        "other", "about", "their", "would", "could", "should", "through",
        "using", "based", "including", "experience", "team", "ability",
    }
    words = set(re.findall(r"\b[a-z]{3,}\b", text))
    return words - stop_words


def score_resume(
    resume_latex: str,
    jd_text: str,
    jd_analysis: dict | None = None,
) -> ATSScoreBreakdown:
    """Score a resume against a job description using ATS heuristics.

    Weights:
        40% keyword match
        20% experience alignment
        10% format quality
        10% action verbs
        10% readability
        10% section completeness

    Args:
        resume_latex: LaTeX source of the resume
        jd_text: Raw job description text
        jd_analysis: Optional structured JD analysis from the pipeline

    Returns:
        ATSScoreBreakdown with detailed scores and feedback
    """
    result = ATSScoreBreakdown()
    resume_text = _extract_text_from_latex(resume_latex)
    jd_lower = jd_text.lower()
    resume_lower = resume_latex.lower()

    # 1. Keyword Match (40%)
    if jd_analysis and jd_analysis.get("required_skills"):
        required = jd_analysis["required_skills"]
        preferred = jd_analysis.get("preferred_skills", [])
        all_skills = required + preferred

        matched = [s for s in all_skills if s.lower() in resume_text]
        missing = [s for s in required if s.lower() not in resume_text]

        result.matched_keywords = matched
        result.missing_keywords = missing

        if all_skills:
            result.keyword_match = len(matched) / len(all_skills)
        else:
            result.keyword_match = 0.5

        if missing:
            result.feedback.append(
                f"Missing {len(missing)} required skills: {', '.join(missing[:5])}"
            )
    else:
        # Fallback: keyword extraction from JD
        jd_keywords = _extract_keywords(jd_lower)
        resume_keywords = _extract_keywords(resume_text)
        if jd_keywords:
            overlap = jd_keywords & resume_keywords
            result.keyword_match = len(overlap) / len(jd_keywords)
            result.matched_keywords = list(overlap)[:20]
            result.missing_keywords = list(jd_keywords - resume_keywords)[:10]
        else:
            result.keyword_match = 0.5

    # 2. Experience Alignment (20%)
    if jd_analysis and jd_analysis.get("experience_level"):
        exp_text = jd_analysis["experience_level"].lower()
        # Look for year numbers in experience level
        year_match = re.search(r"(\d+)", exp_text)
        if year_match:
            required_years = int(year_match.group(1))
            # Check if resume mentions comparable years
            resume_years = re.findall(r"(\d+)\+?\s*years?", resume_text)
            if resume_years:
                max_years = max(int(y) for y in resume_years)
                result.experience_alignment = min(max_years / required_years, 1.0)
            else:
                result.experience_alignment = 0.5
                result.feedback.append("Consider mentioning years of experience explicitly")
        else:
            result.experience_alignment = 0.6
    else:
        result.experience_alignment = 0.6

    # 3. Format Score (10%)
    # Check LaTeX structure quality
    has_itemize = "\\begin{itemize}" in resume_lower or "\\item" in resume_lower
    has_sections = sum(1 for s in EXPECTED_SECTIONS if s in resume_lower) >= 3
    has_hyperlinks = "\\href{" in resume_lower or "\\url{" in resume_lower
    has_dates = bool(re.findall(r"\b20\d{2}\b", resume_latex))

    format_points = sum([has_itemize, has_sections, has_hyperlinks, has_dates])
    result.format_score = format_points / 4

    if not has_itemize:
        result.feedback.append("Use bullet points (\\item) for better ATS parsing")

    # 4. Action Verbs (10%)
    found_verbs = [v for v in ACTION_VERBS if re.search(rf"\b{v}\b", resume_text)]
    result.action_verbs = min(len(found_verbs) / 8, 1.0)

    if len(found_verbs) < 5:
        result.feedback.append(
            f"Use more action verbs ({len(found_verbs)} found, aim for 8+). "
            f"Try: {', '.join(ACTION_VERBS[:5])}"
        )

    # 5. Readability (10%)
    # Check for quantified achievements
    quant_patterns = [
        r"\d+%",       # percentages
        r"\$[\d,]+",    # dollar amounts
        r"\d+x",        # multipliers
        r"\d+\+?\s*(?:users|clients|customers|projects|team|engineers|people)",
    ]
    quant_count = sum(len(re.findall(p, resume_text)) for p in quant_patterns)
    result.readability = min(quant_count / 5, 1.0)

    if quant_count < 3:
        result.feedback.append(
            "Add more quantified achievements (numbers, percentages, metrics)"
        )

    # 6. Section Completeness (10%)
    sections_found = sum(1 for s in EXPECTED_SECTIONS if s in resume_lower)
    result.section_completeness = min(sections_found / 4, 1.0)

    if sections_found < 3:
        missing_sections = [s for s in EXPECTED_SECTIONS[:4] if s not in resume_lower]
        result.feedback.append(
            f"Consider adding sections: {', '.join(missing_sections)}"
        )

    # Calculate weighted overall score
    result.overall = (
        result.keyword_match * 0.40
        + result.experience_alignment * 0.20
        + result.format_score * 0.10
        + result.action_verbs * 0.10
        + result.readability * 0.10
        + result.section_completeness * 0.10
    )
    result.overall = round(result.overall, 3)

    logger.info(
        f"ATS Score: {result.overall:.2f} "
        f"(kw={result.keyword_match:.2f}, exp={result.experience_alignment:.2f}, "
        f"fmt={result.format_score:.2f}, verbs={result.action_verbs:.2f}, "
        f"read={result.readability:.2f}, sect={result.section_completeness:.2f})"
    )

    return result
