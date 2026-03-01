"""Relevance Matcher agent: matches user profile against JD requirements."""

import json
import logging
import time

from agents.schemas import RelevanceMatch
from agents.state import ResumeState

logger = logging.getLogger(__name__)

RELEVANCE_MATCH_PROMPT = """You are a career advisor. Given a candidate's profile and a job description analysis,
determine how well the candidate matches the role.

Candidate Profile:
{user_information}

Job Analysis:
- Title: {job_title}
- Required Skills: {required_skills}
- Preferred Skills: {preferred_skills}
- Experience Level: {experience_level}
- Key Responsibilities: {responsibilities}

Return a JSON object with exactly these fields:
- "matched_skills": Skills the candidate has that match the JD
- "missing_skills": JD skills the candidate lacks
- "relevant_experiences": Candidate experiences most relevant to this role
- "emphasis_points": Points to emphasize in the resume for this specific role
- "match_score": Overall match score from 0.0 to 1.0

Return ONLY the JSON object, no other text."""


async def relevance_matcher_agent(state: ResumeState) -> dict:
    """Match user profile against job requirements.

    Reads: user_information, jd_analysis
    Writes: relevance_match, current_node, agent_outputs
    """
    from services.provider_registry import get_provider_for_agent

    logger.info(f"Task {state['task_number']}: Matching user profile to JD")
    start = time.time()

    jd = state["jd_analysis"]
    provider = get_provider_for_agent("relevance_matcher", state["provider_name"])

    prompt = RELEVANCE_MATCH_PROMPT.format(
        user_information=state.get("user_information", ""),
        job_title=jd.get("job_title", ""),
        required_skills=", ".join(jd.get("required_skills", [])),
        preferred_skills=", ".join(jd.get("preferred_skills", [])),
        experience_level=jd.get("experience_level", ""),
        responsibilities=", ".join(jd.get("key_responsibilities", [])),
    )

    raw = await provider.generate(
        prompt,
        task_id=state["task_id"],
        task_number=state["task_number"],
        response_type="relevance_match",
    )

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
        match = RelevanceMatch(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse relevance match as JSON: {e}. Using fallback.")
        match = RelevanceMatch(
            matched_skills=[],
            missing_skills=[],
            relevant_experiences=[],
            emphasis_points=[],
            match_score=0.5,
        )

    latency = int((time.time() - start) * 1000)
    logger.info(
        f"Task {state['task_number']}: Relevance match complete - "
        f"matched={len(match.matched_skills)}, missing={len(match.missing_skills)}, "
        f"score={match.match_score:.2f}, latency={latency}ms"
    )

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["relevance_matcher"] = {
        "latency_ms": latency,
        "match_score": match.match_score,
        "prompt_chars": len(prompt),
    }
    if hasattr(provider, "last_token_usage") and provider.last_token_usage:
        agent_outputs["relevance_matcher"]["token_usage"] = provider.last_token_usage

    return {
        "relevance_match": match.model_dump(),
        "current_node": "relevance_matcher",
        "agent_outputs": agent_outputs,
    }
