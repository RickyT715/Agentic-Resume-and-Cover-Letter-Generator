"""LLM-as-a-Judge evaluation for resume quality.

Uses a separate LLM call to evaluate the generated resume against
a structured rubric covering keyword alignment, tone, achievements,
relevance, and ATS compliance.
"""

import json
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are an expert resume reviewer and ATS specialist.
Evaluate the following resume against the job description using this rubric:

1. **Keyword Alignment** (0-1): How well does the resume incorporate key terms from the JD?
2. **Professional Tone** (0-1): Is the language professional, active, and confident?
3. **Quantified Achievements** (0-1): Are accomplishments backed by numbers and metrics?
4. **Relevance** (0-1): How relevant is the resume content to the specific role?
5. **ATS Compliance** (0-1): Is the format ATS-friendly (clear sections, standard headings)?

Job Description:
{job_description}

Resume (LaTeX source):
{resume_latex}

Return a JSON object with exactly these fields:
- "keyword_alignment": float 0-1
- "professional_tone": float 0-1
- "quantified_achievements": float 0-1
- "relevance": float 0-1
- "ats_compliance": float 0-1
- "overall_score": float 0-1 (weighted average)
- "reasoning": string (2-3 sentences explaining the scores)
- "improvements": list of strings (3-5 specific actionable improvements)

Return ONLY the JSON object."""


@dataclass
class LLMJudgeResult:
    """Result from LLM-as-judge evaluation."""

    keyword_alignment: float = 0.0
    professional_tone: float = 0.0
    quantified_achievements: float = 0.0
    relevance: float = 0.0
    ats_compliance: float = 0.0
    overall_score: float = 0.0
    reasoning: str = ""
    improvements: list[str] = field(default_factory=list)
    latency_ms: int = 0


async def evaluate_with_llm(
    resume_latex: str,
    job_description: str,
    provider_name: str = "gemini",
    task_id: str = "",
    task_number: int = 0,
) -> LLMJudgeResult:
    """Evaluate a resume using an LLM as a judge.

    Args:
        resume_latex: The LaTeX source of the resume
        job_description: The job description text
        provider_name: Which AI provider to use for evaluation
        task_id: Task ID for logging
        task_number: Task number for logging

    Returns:
        LLMJudgeResult with detailed scores
    """
    from services.provider_registry import get_provider

    logger.info(f"Task {task_number}: Running LLM-as-judge evaluation")
    start = time.time()

    provider = get_provider(provider_name)

    # Truncate LaTeX to avoid token limits
    truncated_latex = resume_latex[:6000]
    truncated_jd = job_description[:3000]

    prompt = JUDGE_PROMPT.format(
        job_description=truncated_jd,
        resume_latex=truncated_latex,
    )

    try:
        raw = await provider.generate(
            prompt,
            task_id=task_id,
            task_number=task_number,
            response_type="llm_judge_eval",
        )

        # Parse JSON response
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)
        result = LLMJudgeResult(
            keyword_alignment=float(data.get("keyword_alignment", 0)),
            professional_tone=float(data.get("professional_tone", 0)),
            quantified_achievements=float(data.get("quantified_achievements", 0)),
            relevance=float(data.get("relevance", 0)),
            ats_compliance=float(data.get("ats_compliance", 0)),
            overall_score=float(data.get("overall_score", 0)),
            reasoning=data.get("reasoning", ""),
            improvements=data.get("improvements", []),
        )

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse LLM judge response: {e}")
        result = LLMJudgeResult(
            overall_score=0.5,
            reasoning="Evaluation parsing failed - using default score",
        )

    result.latency_ms = int((time.time() - start) * 1000)
    logger.info(f"Task {task_number}: LLM judge score={result.overall_score:.2f}, latency={result.latency_ms}ms")

    return result
