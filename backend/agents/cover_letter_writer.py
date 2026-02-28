"""Cover Letter Writer agent: generates a cover letter using resume + JD context."""

import logging
import time

from agents.state import ResumeState

logger = logging.getLogger(__name__)

COVER_LETTER_ENHANCEMENT_PREFIX = """## Job-Specific Cover Letter Instructions

Write a cover letter for the following role:
**Position:** {job_title} at {company_name}
**Key Qualifications to Address:** {emphasis_points}
**Industry:** {industry}

{company_context_section}Focus on how the candidate's relevant experiences directly address the job requirements.

"""


async def cover_letter_writer_agent(state: ResumeState) -> dict:
    """Generate a cover letter based on resume content and JD analysis.

    Reads: resume_text, job_description, language, provider_name, jd_analysis, relevance_match
    Writes: cover_letter_text, current_node, agent_outputs
    """
    from services.prompt_manager import get_prompt_manager
    from services.provider_registry import get_provider_for_agent

    logger.info(f"Task {state['task_number']}: Generating cover letter")
    start = time.time()

    pm = get_prompt_manager()
    provider = get_provider_for_agent("cover_letter_writer", state["provider_name"])

    base_prompt = pm.get_cover_letter_prompt_with_substitutions(
        resume_content=state.get("resume_text", ""),
        job_description=state["job_description"],
        language=state.get("language", "en"),
    )

    # Prepend agent intelligence
    jd = state.get("jd_analysis", {})
    relevance = state.get("relevance_match", {})

    # Include company research context if available
    company_context_section = ""
    if state.get("company_context"):
        company_context_section = (
            f"**Company Research Context:**\n"
            f"Use this information about the company to personalize the cover letter:\n"
            f"{state['company_context'][:2000]}\n\n"
        )

    enhancement = COVER_LETTER_ENHANCEMENT_PREFIX.format(
        job_title=jd.get("job_title", "the target role"),
        company_name=jd.get("company_name", "the company"),
        emphasis_points=", ".join(relevance.get("emphasis_points", [])) or "the candidate's strengths",
        industry=jd.get("industry", ""),
        company_context_section=company_context_section,
    )

    full_prompt = enhancement + base_prompt

    cover_letter_text = await provider.generate(
        full_prompt,
        task_id=state["task_id"],
        task_number=state["task_number"],
        response_type="cover_letter_v3",
    )

    latency = int((time.time() - start) * 1000)
    logger.info(
        f"Task {state['task_number']}: Cover letter generated - "
        f"{len(cover_letter_text)} chars, latency={latency}ms"
    )

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["cover_letter_writer"] = {
        "latency_ms": latency,
        "text_length": len(cover_letter_text),
        "prompt_chars": len(full_prompt),
    }
    if hasattr(provider, 'last_token_usage') and provider.last_token_usage:
        agent_outputs["cover_letter_writer"]["token_usage"] = provider.last_token_usage

    return {
        "cover_letter_text": cover_letter_text,
        "current_node": "cover_letter_writer",
        "agent_outputs": agent_outputs,
    }
