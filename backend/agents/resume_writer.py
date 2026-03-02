"""Resume Writer agent: generates LaTeX resume using existing prompt infrastructure."""

import logging
import time

from agents.state import ResumeState

logger = logging.getLogger(__name__)

RESUME_ENHANCEMENT_PREFIX = """## Job-Specific Optimization Instructions

Based on analysis of the job description, optimize this resume with the following focus:

**Target Role:** {job_title} at {company_name}
**Key Skills to Highlight:** {matched_skills}
**Skills to Incorporate (candidate lacks these but should still include plausibly):** {missing_skills}
**Required Experience Level:** {experience_level}
**Points to Emphasize:** {emphasis_points}

**ATS KEYWORD OPTIMIZATION**: Every skill listed above (both matched and missing) MUST appear verbatim somewhere in the resume — either in the Skills section, bullet points, or project descriptions. ATS systems do exact substring matching, so "Kubernetes" must appear as "Kubernetes", not just "K8s". Include ALL of them.

{company_context_section}{feedback_section}

Now generate the resume following the instructions below:

"""

RESUME_ENHANCEMENT_PREFIX_ZH = """## 针对目标岗位的简历优化指令

根据职位描述分析结果，按照以下要点优化简历：

**目标岗位：** {company_name} - {job_title}
**需要突出的匹配技能：** {matched_skills}
**需要融入的缺失技能（合理体现）：** {missing_skills}
**经验要求：** {experience_level}
**重点突出方向：** {emphasis_points}

**ATS关键词优化要求**：以上列出的所有技能（匹配的和缺失的）必须在简历中原文出现——可以放在技能栏、工作经历的描述中或项目描述里。中国主流ATS系统（北森、Moka等）进行精确关键词匹配，因此"Kubernetes"必须写成"Kubernetes"而非仅写"K8s"，中文技能同理。

**中文简历写作要求**：
- 使用强动词开头（主导、设计、架构、优化、搭建），避免弱动词（参与、协助、了解）
- 每条经历包含量化成果（提升X%、降低Xs、服务X万用户等）
- 技术栈使用中英文双语标注（如"微服务架构(Microservices)"）

{company_context_section}{feedback_section}

现在按照以下指令生成简历：

"""


async def resume_writer_agent(state: ResumeState) -> dict:
    """Generate a LaTeX resume using the existing prompt system + agent intelligence.

    Reads: job_description, template_id, language, provider_name, user_information,
           jd_analysis, relevance_match, resume_prompt (if retry), quality_feedback (if retry)
    Writes: latex_source, resume_prompt, current_node, agent_outputs
    """
    from services.latex_utils import extract_metadata, process_latex_response
    from services.prompt_manager import get_prompt_manager
    from services.provider_registry import get_provider_for_agent
    from services.settings_manager import get_settings_manager

    logger.info(f"Task {state['task_number']}: Generating resume (retry={state.get('retry_count', 0)})")
    start = time.time()

    pm = get_prompt_manager()
    sm = get_settings_manager()
    provider = get_provider_for_agent("resume_writer", state["provider_name"])

    # Build the base prompt using existing infrastructure
    base_prompt = pm.get_resume_prompt_with_substitutions(
        job_description=state["job_description"],
        template_id=state.get("template_id", "classic"),
        language=state.get("language", "en"),
        experience_level=state.get("experience_level", "auto"),
        enforce_one_page=sm.get("enforce_resume_one_page", True),
        allow_fabrication=sm.get("allow_ai_fabrication", True),
    )

    # Prepend agent-specific optimization instructions
    jd = state.get("jd_analysis", {})
    relevance = state.get("relevance_match", {})
    feedback_section = ""

    if state.get("quality_feedback"):
        feedback_section = (
            f"**IMPORTANT - Previous Attempt Feedback:**\n"
            f"The previous resume scored {state.get('quality_score', 0):.2f}/1.0. "
            f"Improvements needed:\n{state['quality_feedback']}\n"
        )

    # Include company research context if available
    company_context_section = ""
    if state.get("company_context"):
        company_context_section = (
            f"**Company Research Context:**\n"
            f"Use the following company information to tailor the resume:\n"
            f"{state['company_context'][:2000]}\n\n"
        )

    language = state.get("language", "en")
    prefix_template = RESUME_ENHANCEMENT_PREFIX_ZH if language == "zh" else RESUME_ENHANCEMENT_PREFIX
    enhancement = prefix_template.format(
        job_title=jd.get("job_title", "the target role"),
        company_name=jd.get("company_name", "the company"),
        matched_skills=", ".join(relevance.get("matched_skills", [])) or "N/A",
        missing_skills=", ".join(relevance.get("missing_skills", [])) or "None",
        experience_level=jd.get("experience_level", "Not specified"),
        emphasis_points="\n- ".join(["", *relevance.get("emphasis_points", [])]) or "N/A",
        match_score=relevance.get("match_score", 0.5),
        company_context_section=company_context_section,
        feedback_section=feedback_section,
    )

    full_prompt = enhancement + base_prompt

    raw_response = await provider.generate(
        full_prompt,
        task_id=state["task_id"],
        task_number=state["task_number"],
        response_type=f"resume_v3_attempt_{state.get('retry_count', 0) + 1}",
    )

    # Extract metadata and process LaTeX
    metadata = extract_metadata(raw_response)
    latex_source = process_latex_response(raw_response)

    # Validate and fix contact header (skip LLM to keep generation fast)
    from services.resume_validator import validate_resume_async

    suffix = "_zh" if language == "zh" else ""
    user_info_text = pm.get_prompt(f"user_information{suffix}")
    latex_source, validation_warnings = await validate_resume_async(
        latex_source,
        user_info_text,
        language,
        sm,
        skip_llm=True,
    )
    if validation_warnings:
        logger.info(f"Task {state['task_number']}: Resume validation warnings: {validation_warnings}")

    latency = int((time.time() - start) * 1000)
    logger.info(f"Task {state['task_number']}: Resume generated - {len(latex_source)} chars, latency={latency}ms")

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["resume_writer"] = {
        "latency_ms": latency,
        "latex_length": len(latex_source),
        "attempt": state.get("retry_count", 0) + 1,
        "prompt_chars": len(full_prompt),
    }
    if hasattr(provider, "last_token_usage") and provider.last_token_usage:
        agent_outputs["resume_writer"]["token_usage"] = provider.last_token_usage

    result: dict = {
        "latex_source": latex_source,
        "resume_prompt": full_prompt,
        "current_node": "resume_writer",
        "agent_outputs": agent_outputs,
    }

    # Update metadata if found
    if metadata.get("company_name"):
        result["company_name"] = metadata["company_name"]
    if metadata.get("position_name"):
        result["position_name"] = metadata["position_name"]

    return result
