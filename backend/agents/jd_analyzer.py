"""JD Analyzer agent: extracts structured information from job descriptions."""

import json
import logging
import time

from agents.schemas import JDAnalysis
from agents.state import ResumeState

logger = logging.getLogger(__name__)

JD_ANALYSIS_PROMPT = """Analyze the following job description and extract structured information.

Return a JSON object with exactly these fields:
- "job_title": The job title
- "company_name": Company name (empty string if not found)
- "required_skills": List of required technical and soft skills
- "preferred_skills": List of nice-to-have skills
- "experience_level": Required experience level (e.g., "3-5 years", "senior")
- "key_responsibilities": List of main job responsibilities
- "industry": Industry sector (e.g., "Technology", "Finance")

Job Description:
{job_description}

Return ONLY the JSON object, no other text."""


async def jd_analyzer_agent(state: ResumeState) -> dict:
    """Extract structured information from a job description.

    Reads: job_description
    Writes: jd_analysis, company_name, position_name, current_node, agent_outputs
    """
    from services.provider_registry import get_provider

    logger.info(f"Task {state['task_number']}: Analyzing job description")
    start = time.time()

    provider = get_provider(state["provider_name"])
    prompt = JD_ANALYSIS_PROMPT.format(job_description=state["job_description"])

    raw = await provider.generate(
        prompt,
        task_id=state["task_id"],
        task_number=state["task_number"],
        response_type="jd_analysis",
    )

    # Parse JSON response - handle markdown code blocks
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
        analysis = JDAnalysis(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse JD analysis as JSON: {e}. Using fallback.")
        analysis = JDAnalysis(
            job_title="Unknown Position",
            company_name="",
            required_skills=[],
            preferred_skills=[],
            experience_level="",
            key_responsibilities=[],
            industry="",
        )

    latency = int((time.time() - start) * 1000)
    logger.info(
        f"Task {state['task_number']}: JD analysis complete - "
        f"title={analysis.job_title!r}, skills={len(analysis.required_skills)}, "
        f"latency={latency}ms"
    )

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["jd_analyzer"] = {
        "latency_ms": latency,
        "skills_found": len(analysis.required_skills) + len(analysis.preferred_skills),
    }

    return {
        "jd_analysis": analysis.model_dump(),
        "company_name": analysis.company_name,
        "position_name": analysis.job_title,
        "current_node": "jd_analyzer",
        "agent_outputs": agent_outputs,
    }
