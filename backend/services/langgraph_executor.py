"""LangGraph executor service: runs the multi-agent pipeline for a task."""

import logging
from datetime import datetime

from agents.graph import get_resume_graph
from agents.state import ResumeState
from models.task import Task, TaskStatus, TaskStep
from services.prompt_manager import get_prompt_manager
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

# Map LangGraph node names to v2 TaskStep values for progress broadcasting
NODE_TO_STEP = {
    "jd_analyzer": TaskStep.GENERATE_RESUME,
    "relevance_matcher": TaskStep.GENERATE_RESUME,
    "resume_writer": TaskStep.GENERATE_RESUME,
    "quality_gate": TaskStep.GENERATE_RESUME,
    "compile_latex": TaskStep.COMPILE_LATEX,
    "extract_text": TaskStep.EXTRACT_TEXT,
    "cover_letter_writer": TaskStep.GENERATE_COVER_LETTER,
    "create_cover_pdf": TaskStep.CREATE_COVER_PDF,
    "finalize": TaskStep.COMPILE_LATEX,
}

# Human-readable descriptions for each node
NODE_DESCRIPTIONS = {
    "jd_analyzer": "Analyzing job description...",
    "relevance_matcher": "Matching your profile to job requirements...",
    "resume_writer": "Generating tailored resume...",
    "quality_gate": "Evaluating resume quality...",
    "compile_latex": "Compiling LaTeX to PDF...",
    "extract_text": "Extracting resume text for cover letter...",
    "cover_letter_writer": "Generating cover letter...",
    "create_cover_pdf": "Creating cover letter PDF...",
    "finalize": "Finalizing outputs...",
}


async def run_langgraph_pipeline(
    task: Task,
    progress_callback=None,
) -> Task:
    """Run the LangGraph multi-agent pipeline for a generation task.

    Args:
        task: The Task object to process
        progress_callback: Optional async callback(update_dict) for progress

    Returns:
        The updated Task object
    """
    logger.info(f"Task {task.task_number}: Starting v3 LangGraph pipeline")
    start_time = datetime.now()

    # Resolve provider
    sm = get_settings_manager()
    provider_name = task.provider or sm.get("default_provider") or "gemini"

    # Load user information
    pm = get_prompt_manager()
    suffix = "_zh" if task.language == "zh" else ""
    user_info = pm.get_prompt(f"user_information{suffix}")

    # Build initial state
    initial_state: ResumeState = {
        "task_id": task.id,
        "task_number": task.task_number,
        "job_description": task.job_description,
        "language": task.language,
        "template_id": task.template_id,
        "generate_cover_letter": task.generate_cover_letter,
        "provider_name": provider_name,
        "user_information": user_info,
        "retry_count": 0,
        "agent_outputs": {},
    }

    graph = get_resume_graph()
    task.status = TaskStatus.RUNNING
    task.pipeline_version = "v3"

    try:
        # Stream updates from the graph for progress tracking
        final_state = None
        async for event in graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name == "__end__":
                    continue

                description = NODE_DESCRIPTIONS.get(node_name, f"Running {node_name}...")
                step = NODE_TO_STEP.get(node_name, TaskStep.GENERATE_RESUME)

                logger.info(f"Task {task.task_number}: Node '{node_name}' completed")

                # Broadcast progress
                if progress_callback:
                    await progress_callback({
                        "task_id": task.id,
                        "task_number": task.task_number,
                        "step": step.value,
                        "status": TaskStatus.RUNNING.value,
                        "message": description,
                        "node": node_name,
                        "pipeline_version": "v3",
                    })

                # Update step progress on the task
                for s in task.steps:
                    if s.step == step and s.status != TaskStatus.COMPLETED:
                        s.status = TaskStatus.RUNNING
                        s.message = description
                        s.started_at = s.started_at or datetime.now()
                        break

                final_state = node_output

        # Collect final state from the last event
        # We need to get the accumulated state, so run once more
        # Actually astream with "updates" gives per-node diffs. Let's invoke instead for final state.
        # Re-run to get complete state (astream already ran it, so let's collect from events)

        # The final_state from streaming is only the last node's output.
        # For the full state, we invoke the graph synchronously.
        full_result = await graph.ainvoke(initial_state)

        # Apply results to task
        if full_result.get("error"):
            task.status = TaskStatus.FAILED
            task.error_message = full_result["error"]
        else:
            task.status = TaskStatus.COMPLETED
            task.resume_pdf_path = full_result.get("resume_pdf_path")
            task.cover_letter_pdf_path = full_result.get("cover_letter_pdf_path")
            task.latex_source = full_result.get("latex_source")
            if full_result.get("company_name"):
                task.company_name = full_result["company_name"]
            if full_result.get("position_name"):
                task.position_name = full_result["position_name"]

        # Mark all steps as completed
        for s in task.steps:
            if task.status == TaskStatus.COMPLETED:
                s.status = TaskStatus.COMPLETED
                s.completed_at = datetime.now()
            elif s.status == TaskStatus.RUNNING:
                s.status = TaskStatus.FAILED
                s.message = task.error_message or "Pipeline failed"

    except Exception as e:
        logger.error(f"Task {task.task_number}: LangGraph pipeline failed: {e}", exc_info=True)
        task.status = TaskStatus.FAILED
        task.error_message = str(e)

        for s in task.steps:
            if s.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                s.status = TaskStatus.FAILED
                s.message = str(e)

    task.completed_at = datetime.now()
    elapsed = (task.completed_at - start_time).total_seconds()
    logger.info(
        f"Task {task.task_number}: Pipeline {task.status.value} in {elapsed:.2f}s"
    )

    # Broadcast final status
    if progress_callback:
        final_step = task.steps[-1].step if task.steps else TaskStep.COMPILE_LATEX
        await progress_callback({
            "task_id": task.id,
            "task_number": task.task_number,
            "step": final_step.value,
            "status": task.status.value,
            "message": f"Pipeline {task.status.value}",
            "pipeline_version": "v3",
        })

    return task
