"""LangGraph tool nodes for RAG retrieval.

Provides a retrieval node that can be inserted into the resume generation graph.
"""

import logging

from agents.state import ResumeState

logger = logging.getLogger(__name__)


async def retrieve_company_context_node(state: ResumeState) -> dict:
    """LangGraph node: retrieve company context from the vector store.

    Reads: job_description, jd_analysis (company_name)
    Writes: company_context, current_node, agent_outputs
    """
    import time

    from rag.retriever import retrieve_company_context

    start = time.time()
    company_name = state.get("company_name", "")
    jd_analysis = state.get("jd_analysis", {})

    # Try to get company name from various sources
    if not company_name:
        company_name = jd_analysis.get("company_name", "")

    logger.info(f"Task {state.get('task_number', '?')}: Retrieving company context for '{company_name}'")

    context = await retrieve_company_context(
        job_description=state["job_description"],
        company_name=company_name if company_name else None,
    )

    latency = int((time.time() - start) * 1000)

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["company_research"] = {
        "latency_ms": latency,
        "has_context": context is not None,
        "context_length": len(context) if context else 0,
    }

    logger.info(
        f"Task {state.get('task_number', '?')}: Company context retrieval - "
        f"found={'yes' if context else 'no'}, latency={latency}ms"
    )

    return {
        "company_context": context,
        "current_node": "company_research",
        "agent_outputs": agent_outputs,
    }


def should_retrieve_company(state: ResumeState) -> str:
    """Conditional edge: decide whether to retrieve company context.

    Returns "retrieve_company" if company data exists in the vector store,
    otherwise skips to "resume_writer".
    """
    company_name = state.get("company_name", "")
    jd_analysis = state.get("jd_analysis", {})
    if not company_name:
        company_name = jd_analysis.get("company_name", "")

    if not company_name:
        return "resume_writer"

    # Check if we have data for this company
    try:
        from rag.vector_store import get_company_info

        docs = get_company_info(company_name)
        if docs:
            return "retrieve_company"
    except Exception as e:
        logger.debug(f"Vector store check failed (likely not installed): {e}")

    return "resume_writer"
