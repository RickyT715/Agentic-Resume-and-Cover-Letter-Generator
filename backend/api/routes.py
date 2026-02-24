from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, PlainTextResponse
from typing import List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from models.task import Task, TaskCreate, TaskUpdate, ApplicationQuestion
from services.task_manager import task_manager
from services.settings_manager import get_settings_manager
from services.prompt_manager import get_prompt_manager

router = APIRouter(prefix="/api")


# ============== Request Models ==============

class JobDescriptionUpdate(BaseModel):
    job_description: str


class TaskSettingsUpdate(BaseModel):
    job_description: Optional[str] = None
    generate_cover_letter: Optional[bool] = None
    template_id: Optional[str] = None
    language: Optional[str] = None
    provider: Optional[str] = None


class AppSettingsUpdate(BaseModel):
    # Provider Selection
    default_provider: Optional[str] = None
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_temperature: Optional[float] = None
    gemini_top_k: Optional[int] = None
    gemini_top_p: Optional[float] = None
    gemini_max_output_tokens: Optional[int] = None
    gemini_thinking_level: Optional[str] = None
    gemini_enable_search: Optional[bool] = None
    # Claude
    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    claude_temperature: Optional[float] = None
    claude_max_output_tokens: Optional[int] = None
    claude_extended_thinking: Optional[bool] = None
    claude_thinking_budget: Optional[int] = None
    # OpenAI-Compatible
    openai_compat_base_url: Optional[str] = None
    openai_compat_api_key: Optional[str] = None
    openai_compat_model: Optional[str] = None
    openai_compat_temperature: Optional[float] = None
    openai_compat_max_output_tokens: Optional[int] = None
    # Claude Code Proxy
    claude_proxy_base_url: Optional[str] = None
    claude_proxy_api_key: Optional[str] = None
    claude_proxy_model: Optional[str] = None
    claude_proxy_temperature: Optional[float] = None
    claude_proxy_max_output_tokens: Optional[int] = None
    # General
    enforce_resume_one_page: Optional[bool] = None
    enforce_cover_letter_one_page: Optional[bool] = None
    max_page_retry_attempts: Optional[int] = None
    generate_cover_letter: Optional[bool] = None
    max_latex_retries: Optional[int] = None
    default_template_id: Optional[str] = None


class AddQuestionRequest(BaseModel):
    question: str
    word_limit: int = 150


class UpdateQuestionRequest(BaseModel):
    question: Optional[str] = None
    word_limit: Optional[int] = None


class CompanyScrapeRequest(BaseModel):
    url: str
    company_name: str


class PromptUpdate(BaseModel):
    content: str


# ============== Settings Endpoints ==============

@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    settings_manager = get_settings_manager()
    return settings_manager.get_all(mask_api_key=True)


@router.put("/settings")
async def update_settings(data: AppSettingsUpdate) -> Dict[str, Any]:
    settings_manager = get_settings_manager()
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return settings_manager.get_all(mask_api_key=True)
    settings_manager.update(updates)
    return settings_manager.get_all(mask_api_key=True)


@router.post("/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    settings_manager = get_settings_manager()
    settings_manager.reset_to_defaults()
    return settings_manager.get_all(mask_api_key=True)


# ============== Prompts Endpoints ==============

VALID_PROMPT_KEYS = [
    "resume_prompt", "cover_letter_prompt", "user_information", "resume_format", "application_question_prompt",
    "resume_prompt_zh", "cover_letter_prompt_zh", "user_information_zh", "resume_format_zh", "application_question_prompt_zh",
]


@router.get("/prompts")
async def get_prompts() -> Dict[str, str]:
    prompt_manager = get_prompt_manager()
    return prompt_manager.get_all_prompts()


@router.get("/prompts/{prompt_key}")
async def get_prompt(prompt_key: str) -> Dict[str, str]:
    if prompt_key not in VALID_PROMPT_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid prompt key. Valid: {VALID_PROMPT_KEYS}")
    prompt_manager = get_prompt_manager()
    content = prompt_manager.get_prompt(prompt_key)
    return {"key": prompt_key, "content": content}


@router.put("/prompts/{prompt_key}")
async def update_prompt(prompt_key: str, data: PromptUpdate) -> Dict[str, Any]:
    if prompt_key not in VALID_PROMPT_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid prompt key. Valid: {VALID_PROMPT_KEYS}")

    prompt_manager = get_prompt_manager()

    # Validate placeholders
    warnings = prompt_manager.validate_prompt(prompt_key, data.content)

    success = prompt_manager.update_prompt(prompt_key, data.content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update prompt")

    result = {
        "key": prompt_key,
        "content": data.content,
        "message": "Prompt updated successfully",
    }
    if warnings:
        result["warnings"] = warnings
    return result


@router.post("/prompts/reload")
async def reload_prompts() -> Dict[str, str]:
    prompt_manager = get_prompt_manager()
    prompt_manager.reload_prompts()
    return {"message": "Prompts reloaded successfully"}


# ============== Provider Endpoints ==============

@router.get("/providers")
async def get_providers() -> List[dict]:
    from services.provider_registry import AVAILABLE_PROVIDERS
    return AVAILABLE_PROVIDERS


# ============== Template Endpoints ==============

@router.get("/templates")
async def get_templates() -> List[dict]:
    return task_manager.get_available_templates()


# ============== JD History Endpoints ==============

@router.get("/jd-history")
async def get_jd_history() -> List[dict]:
    return task_manager.get_jd_history()


# ============== Task Endpoints ==============

@router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate):
    task = task_manager.create_task(task_data)
    return task


@router.get("/tasks", response_model=List[Task])
async def get_tasks():
    return task_manager.get_all_tasks()


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    success = task_manager.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or is currently running")
    return {"message": "Task deleted"}


@router.delete("/tasks")
async def delete_completed_tasks():
    count = task_manager.delete_completed_tasks()
    return {"message": f"Deleted {count} tasks", "count": count}


@router.put("/tasks/{task_id}/job-description")
async def update_job_description(task_id: str, data: JobDescriptionUpdate):
    task = task_manager.update_task_job_description(task_id, data.job_description)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or already started")
    return task


@router.put("/tasks/{task_id}/settings")
async def update_task_settings(task_id: str, data: TaskSettingsUpdate):
    task = task_manager.update_task_settings(
        task_id,
        job_description=data.job_description,
        generate_cover_letter=data.generate_cover_letter,
        template_id=data.template_id,
        language=data.language,
        provider=data.provider,
    )
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or already started")
    return task


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: str, background_tasks: BackgroundTasks):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task already started or completed")
    if not task.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    background_tasks.add_task(task_manager.run_task, task_id)
    return {"message": "Task started", "task_id": task_id}


@router.post("/tasks/{task_id}/start-v3")
async def start_task_v3(task_id: str, background_tasks: BackgroundTasks):
    """Start a task using the v3 LangGraph multi-agent pipeline."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task already started or completed")
    if not task.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    background_tasks.add_task(task_manager.run_task_v3, task_id)
    return {"message": "Task started (v3 pipeline)", "task_id": task_id, "pipeline": "v3"}


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    task = task_manager.retry_task(task_id)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or cannot be retried")
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = task_manager.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or cannot be cancelled")
    return task


@router.get("/tasks/{task_id}/resume")
async def download_resume(task_id: str, inline: bool = Query(False)):
    task = task_manager.get_task(task_id)
    if not task or not task.resume_pdf_path:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = Path(task.resume_pdf_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resume file not found")

    return FileResponse(
        task.resume_pdf_path,
        media_type="application/pdf",
        filename=file_path.name,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/tasks/{task_id}/cover-letter")
async def download_cover_letter(task_id: str, inline: bool = Query(False)):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.generate_cover_letter:
        raise HTTPException(status_code=400, detail="Cover letter was not enabled for this task")
    if not task.cover_letter_pdf_path:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    file_path = Path(task.cover_letter_pdf_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Cover letter file not found")

    return FileResponse(
        task.cover_letter_pdf_path,
        media_type="application/pdf",
        filename=file_path.name,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/tasks/{task_id}/latex")
async def download_latex(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.latex_source:
        raise HTTPException(status_code=404, detail="LaTeX source not available")

    if task.company_name and task.position_name:
        tex_name = f"resume_{task.company_name}_{task.position_name}.tex"
    elif task.company_name:
        tex_name = f"resume_{task.company_name}.tex"
    else:
        tex_name = f"resume_task_{task.task_number}.tex"
    # Sanitize for header safety
    tex_name = tex_name.replace('"', '').replace('\n', '').replace('\r', '')

    return PlainTextResponse(
        content=task.latex_source,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{tex_name}"'},
    )


@router.get("/tasks/{task_id}/failed-latex")
async def get_failed_latex(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"failed_attempts": task.failed_latex_attempts}


# ============== Application Questions Endpoints ==============

@router.get("/tasks/{task_id}/questions", response_model=list[ApplicationQuestion])
async def get_questions(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.questions


@router.post("/tasks/{task_id}/questions", response_model=ApplicationQuestion)
async def add_question(task_id: str, data: AddQuestionRequest):
    q = task_manager.add_question(task_id, data.question, data.word_limit)
    if not q:
        raise HTTPException(status_code=404, detail="Task not found")
    return q


@router.put("/tasks/{task_id}/questions/{question_id}", response_model=ApplicationQuestion)
async def update_question(task_id: str, question_id: str, data: UpdateQuestionRequest):
    q = task_manager.update_question(
        task_id, question_id,
        question=data.question,
        word_limit=data.word_limit
    )
    if not q:
        raise HTTPException(status_code=404, detail="Task or question not found")
    return q


@router.delete("/tasks/{task_id}/questions/{question_id}")
async def delete_question(task_id: str, question_id: str):
    success = task_manager.delete_question(task_id, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task or question not found")
    return {"message": "Question deleted"}


# ============== Evaluation Endpoints ==============

@router.get("/tasks/{task_id}/evaluation")
async def get_evaluation(task_id: str):
    """Get ATS evaluation score breakdown for a completed task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.latex_source:
        raise HTTPException(status_code=400, detail="No resume available for evaluation")

    from evaluation.metrics import evaluate_resume

    result = await evaluate_resume(
        resume_latex=task.latex_source,
        job_description=task.job_description,
        use_llm_judge=False,  # GET endpoint uses fast ATS-only scoring
    )
    return result


@router.post("/tasks/{task_id}/evaluate")
async def evaluate_task(task_id: str):
    """Run full evaluation (ATS + LLM judge) on an existing resume."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.latex_source:
        raise HTTPException(status_code=400, detail="No resume available for evaluation")

    from evaluation.metrics import evaluate_resume

    result = await evaluate_resume(
        resume_latex=task.latex_source,
        job_description=task.job_description,
        provider_name=task.provider,
        task_id=task.id,
        task_number=task.task_number,
        use_llm_judge=True,
    )
    return result


# ============== Company Research (RAG) Endpoints ==============

@router.post("/companies/scrape")
async def scrape_company(data: CompanyScrapeRequest):
    """Scrape a company website and index it for RAG retrieval."""
    try:
        from rag.retriever import scrape_and_index_company
        result = await scrape_and_index_company(data.url, data.company_name)
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="RAG module not installed (chromadb required)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/companies/{company_name}/info")
async def get_company_info(company_name: str):
    """Get indexed company data from the vector store."""
    try:
        from rag.vector_store import get_company_info as _get_info
        docs = _get_info(company_name)
        return {"company_name": company_name, "documents": len(docs), "chunks": docs}
    except ImportError:
        raise HTTPException(status_code=501, detail="RAG module not installed")


@router.delete("/companies/{company_name}")
async def delete_company_data(company_name: str):
    """Delete all indexed data for a company."""
    try:
        from rag.vector_store import delete_company
        count = delete_company(company_name)
        return {"message": f"Deleted {count} documents", "count": count}
    except ImportError:
        raise HTTPException(status_code=501, detail="RAG module not installed")


@router.get("/companies")
async def list_companies():
    """List all companies with indexed data."""
    try:
        from rag.vector_store import list_companies as _list
        return {"companies": _list()}
    except ImportError:
        return {"companies": []}


# ============== Application Questions Endpoints ==============

@router.post("/tasks/{task_id}/questions/{question_id}/generate", response_model=ApplicationQuestion)
async def generate_question_answer(task_id: str, question_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required to generate answers")
    q = await task_manager.generate_question_answer(task_id, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.post("/tasks/{task_id}/questions/generate-all")
async def generate_all_question_answers(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required to generate answers")

    results = []
    for q in task.questions:
        if q.status != "completed" or q.answer is None:
            result = await task_manager.generate_question_answer(task_id, q.id)
            if result:
                results.append(result)
    return task.questions
