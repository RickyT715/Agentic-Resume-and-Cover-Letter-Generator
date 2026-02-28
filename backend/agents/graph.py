"""LangGraph StateGraph definition for the resume generation pipeline.

Pipeline:
    JD Analyzer -> Relevance Matcher -> [Company Research?] -> Resume Writer -> Quality Gate
        -> (retry?) -> Compile LaTeX -> [Extract Text -> Cover Letter Writer
        -> Create Cover PDF] -> Finalize

The quality gate uses conditional routing to optionally retry resume generation.
Cover letter nodes are only traversed if generate_cover_letter=True.
Company research has two paths:
  1. Manual RAG: runs if company data exists in the vector store (pre-indexed)
  2. Auto search: uses Gemini Search Grounding to research the company in real time
If neither is available, the pipeline skips directly to resume_writer.
"""

import logging

from langgraph.graph import END, StateGraph

from agents.company_researcher import auto_company_research_agent
from agents.cover_letter_writer import cover_letter_writer_agent
from agents.finalize import (
    compile_latex_node,
    create_cover_letter_pdf_node,
    extract_text_node,
    finalize_node,
)
from agents.jd_analyzer import jd_analyzer_agent
from agents.quality_gate import quality_gate_node, should_retry
from agents.relevance_matcher import relevance_matcher_agent
from agents.resume_writer import resume_writer_agent
from agents.state import ResumeState

logger = logging.getLogger(__name__)


def _should_retrieve_company(state: ResumeState) -> str:
    """Conditional edge: decide whether to retrieve company context.

    Priority:
      1. Vector store has pre-indexed data -> "retrieve_company"
      2. Company name extracted from JD     -> "auto_company_research"
      3. No company info available          -> "resume_writer"
    """
    company_name = state.get("company_name", "")
    jd_analysis = state.get("jd_analysis", {})
    if not company_name:
        company_name = jd_analysis.get("company_name", "")

    if not company_name:
        return "resume_writer"

    # Check vector store first (existing manual RAG path)
    try:
        from rag.vector_store import get_company_info
        docs = get_company_info(company_name)
        if docs:
            return "retrieve_company"
    except Exception:
        pass

    # Fall back to auto search grounding
    return "auto_company_research"


def _should_generate_cover_letter(state: ResumeState) -> str:
    """Conditional edge: skip cover letter if not requested or if there's an error."""
    if state.get("error"):
        return "finalize"
    if state.get("generate_cover_letter", True):
        return "extract_text"
    return "finalize"


def build_resume_graph() -> StateGraph:
    """Build and compile the LangGraph pipeline for resume generation.

    Returns a compiled StateGraph ready for invocation.
    """
    graph = StateGraph(ResumeState)

    # Add nodes
    graph.add_node("jd_analyzer", jd_analyzer_agent)
    graph.add_node("relevance_matcher", relevance_matcher_agent)
    graph.add_node("resume_writer", resume_writer_agent)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("compile_latex", compile_latex_node)
    graph.add_node("extract_text", extract_text_node)
    graph.add_node("cover_letter_writer", cover_letter_writer_agent)
    graph.add_node("create_cover_pdf", create_cover_letter_pdf_node)
    graph.add_node("finalize", finalize_node)

    # Add auto company research node (always available)
    graph.add_node("auto_company_research", auto_company_research_agent)

    # Add optional RAG retrieval node
    try:
        from rag.tools import retrieve_company_context_node
        graph.add_node("retrieve_company", retrieve_company_context_node)
        has_rag = True
    except ImportError:
        has_rag = False
        logger.info("RAG module not available, skipping company research node")

    # Set entry point
    graph.set_entry_point("jd_analyzer")

    # Linear edges
    graph.add_edge("jd_analyzer", "relevance_matcher")

    # After relevance matching, conditionally route to company research
    conditional_map = {
        "auto_company_research": "auto_company_research",
        "resume_writer": "resume_writer",
    }
    if has_rag:
        conditional_map["retrieve_company"] = "retrieve_company"

    graph.add_conditional_edges(
        "relevance_matcher",
        _should_retrieve_company,
        conditional_map,
    )

    # Both company research paths lead to resume_writer
    graph.add_edge("auto_company_research", "resume_writer")
    if has_rag:
        graph.add_edge("retrieve_company", "resume_writer")

    graph.add_edge("resume_writer", "quality_gate")

    # Conditional edge: quality gate -> retry or continue
    graph.add_conditional_edges(
        "quality_gate",
        should_retry,
        {
            "resume_writer": "resume_writer",
            "compile_latex": "compile_latex",
        },
    )

    # After compilation: decide cover letter or finalize
    graph.add_conditional_edges(
        "compile_latex",
        _should_generate_cover_letter,
        {
            "extract_text": "extract_text",
            "finalize": "finalize",
        },
    )

    # Cover letter sub-pipeline
    graph.add_edge("extract_text", "cover_letter_writer")
    graph.add_edge("cover_letter_writer", "create_cover_pdf")
    graph.add_edge("create_cover_pdf", "finalize")

    # Finalize -> END
    graph.add_edge("finalize", END)

    logger.info("Resume generation graph built successfully")
    return graph.compile()


# Module-level compiled graph (singleton)
_compiled_graph = None


def get_resume_graph():
    """Get the compiled resume generation graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_resume_graph()
    return _compiled_graph
