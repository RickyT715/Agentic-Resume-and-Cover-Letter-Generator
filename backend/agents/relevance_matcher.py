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

RELEVANCE_MATCH_PROMPT_ZH = """你是一位资深职业顾问。根据候选人的背景资料和职位分析结果，评估候选人与目标岗位的匹配程度。

候选人资料：
{user_information}

职位分析：
- 职位名称：{job_title}
- 必需技能：{required_skills}
- 加分技能：{preferred_skills}
- 经验要求：{experience_level}
- 主要职责：{responsibilities}

返回一个JSON对象，包含以下字段：
- "matched_skills": 候选人与JD匹配的技能列表
- "missing_skills": 候选人缺少的JD技能列表
- "relevant_experiences": 与目标岗位最相关的候选人经历
- "emphasis_points": 简历中应重点突出的方面
- "match_score": 综合匹配度评分（0.0到1.0）

仅返回JSON对象，不要包含其他文字。"""


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
    language = state.get("language", "en")
    prompt_template = RELEVANCE_MATCH_PROMPT_ZH if language == "zh" else RELEVANCE_MATCH_PROMPT

    prompt = prompt_template.format(
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
