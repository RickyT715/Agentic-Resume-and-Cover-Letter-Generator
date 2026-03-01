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

COMPANY_RESEARCH_PROMPT_ZH = """调研公司"{company_name}"，提供简要概况，涵盖以下方面：

1. **公司业务**：核心产品/服务、所处行业、市场地位
2. **技术栈**：已知使用的技术、编程语言、框架
3. **企业文化**：公司文化、使命愿景、工作环境
4. **最新动态**：近期重要发展、融资情况、新产品发布

请用中文回答，内容准确简练（800字以内）。重点关注对求职{job_title}岗位有帮助的信息。

如果无法找到该公司的可靠信息，仅回复"未找到可靠信息。"，不要添加其他内容。"""


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

    language = state.get("language", "en")
    provider = get_provider_for_agent("company_researcher", state["provider_name"])
    prompt_template = COMPANY_RESEARCH_PROMPT_ZH if language == "zh" else COMPANY_RESEARCH_PROMPT
    prompt = prompt_template.format(
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
            f"Provider '{state['provider_name']}' does not support enable_search, falling back to standard generation"
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
    raw_stripped = raw.strip().lower() if raw else ""
    if raw and "no reliable information found" not in raw_stripped and "未找到可靠信息" not in raw_stripped:
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
