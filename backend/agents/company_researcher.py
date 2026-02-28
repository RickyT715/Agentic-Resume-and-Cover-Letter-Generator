"""Auto Company Research agent: researches company using Gemini Search Grounding.

Uses the provider's search grounding (Google Search) to gather real-time
company information when no pre-indexed data exists in the vector store.
"""

import logging
import time

from agents.state import ResumeState

logger = logging.getLogger(__name__)

COMPANY_RESEARCH_PROMPT = """Research the company "{company_name}" and provide a concise summary covering:

1. **What they do**: Core products/services, industry, and market position
2. **Tech stack**: Known technologies, programming languages, frameworks
3. **Culture & Values**: Company culture, mission statement, work environment
4. **Recent news**: Any recent notable developments, funding, product launches

Keep the response factual and concise (under 800 words). Focus on information useful for tailoring a job application for a {job_title} role.

If you cannot find reliable information about this company, say "No reliable information found." and nothing else."""


async def auto_company_research_agent(state: ResumeState) -> dict:
    """Research company using search grounding when no vector store data exists.

    Reads: company_name, jd_analysis, provider_name
    Writes: company_context, current_node, agent_outputs
    """
    from services.provider_registry import get_provider_for_agent

    start = time.time()

    company_name = state.get("company_name", "")
    jd_analysis = state.get("jd_analysis", {})
    if not company_name:
        company_name = jd_analysis.get("company_name", "")

    job_title = jd_analysis.get("job_title", "this")
    task_number = state.get("task_number", "?")

    logger.info(f"Task {task_number}: Auto-researching company '{company_name}'")

    provider = get_provider_for_agent("company_researcher", state["provider_name"])
    prompt = COMPANY_RESEARCH_PROMPT.format(
        company_name=company_name,
        job_title=job_title,
    )

    try:
        raw = await provider.generate(
            prompt,
            task_id=state.get("task_id"),
            task_number=state.get("task_number"),
            response_type="company_research",
            enable_search=True,
        )
    except TypeError:
        # Provider doesn't accept enable_search kwarg — call without it
        logger.debug(
            f"Provider '{state['provider_name']}' does not support enable_search, "
            "falling back to standard generation"
        )
        raw = await provider.generate(
            prompt,
            task_id=state.get("task_id"),
            task_number=state.get("task_number"),
            response_type="company_research",
        )

    latency = int((time.time() - start) * 1000)

    # If the model couldn't find info, treat as no context
    context = None
    if raw and "no reliable information found" not in raw.strip().lower():
        context = raw.strip()

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["auto_company_research"] = {
        "latency_ms": latency,
        "has_context": context is not None,
        "context_length": len(context) if context else 0,
        "company_name": company_name,
    }

    logger.info(
        f"Task {task_number}: Auto company research complete - "
        f"company='{company_name}', found={'yes' if context else 'no'}, "
        f"latency={latency}ms"
    )

    return {
        "company_context": context,
        "current_node": "auto_company_research",
        "agent_outputs": agent_outputs,
    }
