import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from middleware.auth import require_api_key
from middleware.rate_limit import SCRAPE_RATE, TASK_CREATE_RATE, rate_limit
from models.task import ApplicationQuestion, Task, TaskCreate
from services.prompt_manager import get_prompt_manager
from services.settings_manager import get_settings_manager
from services.task_manager import task_manager

router = APIRouter(prefix="/api")

# Private IP ranges blocked for SSRF protection
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_url_not_internal(url: str) -> None:
    """Raise HTTPException 400 if the URL resolves to a private/internal address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing hostname")
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Could not resolve hostname")
    for _, _, _, _, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in _PRIVATE_NETWORKS:
            if ip in network:
                raise HTTPException(status_code=400, detail="URL resolves to a private/internal address")


# ============== Request Models ==============


class JobDescriptionUpdate(BaseModel):
    job_description: str


class TaskSettingsUpdate(BaseModel):
    job_description: str | None = None
    generate_cover_letter: bool | None = None
    template_id: str | None = None
    language: str | None = None
    experience_level: str | None = None
    provider: str | None = None


class AppSettingsUpdate(BaseModel):
    # Provider Selection
    default_provider: str | None = None
    # Gemini
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    gemini_temperature: float | None = None
    gemini_top_k: int | None = None
    gemini_top_p: float | None = None
    gemini_max_output_tokens: int | None = None
    gemini_thinking_level: str | None = None
    gemini_enable_search: bool | None = None
    # Claude
    claude_api_key: str | None = None
    claude_model: str | None = None
    claude_temperature: float | None = None
    claude_max_output_tokens: int | None = None
    claude_extended_thinking: bool | None = None
    claude_thinking_budget: int | None = None
    # OpenAI-Compatible
    openai_compat_base_url: str | None = None
    openai_compat_api_key: str | None = None
    openai_compat_model: str | None = None
    openai_compat_temperature: float | None = None
    openai_compat_max_output_tokens: int | None = None
    # Claude Code Proxy
    claude_proxy_base_url: str | None = None
    claude_proxy_api_key: str | None = None
    claude_proxy_model: str | None = None
    claude_proxy_temperature: float | None = None
    claude_proxy_max_output_tokens: int | None = None
    # DeepSeek
    deepseek_api_key: str | None = None
    deepseek_model: str | None = None
    deepseek_temperature: float | None = None
    deepseek_max_output_tokens: int | None = None
    # Qwen
    qwen_api_key: str | None = None
    qwen_model: str | None = None
    qwen_temperature: float | None = None
    qwen_max_output_tokens: int | None = None
    # General
    enforce_resume_one_page: bool | None = None
    enforce_cover_letter_one_page: bool | None = None
    max_page_retry_attempts: int | None = None
    generate_cover_letter: bool | None = None
    max_latex_retries: int | None = None
    default_template_id: str | None = None
    default_experience_level: str | None = None
    allow_ai_fabrication: bool | None = None
    # Resume Validation
    enable_contact_replacement: bool | None = None
    enable_text_validation: bool | None = None
    enable_llm_validation: bool | None = None
    # User Profile Links
    user_linkedin_url: str | None = None
    user_github_url: str | None = None
    # Per-Agent Provider Overrides
    agent_providers: dict[str, str] | None = None


class AddQuestionRequest(BaseModel):
    question: str
    word_limit: int = 150


class UpdateQuestionRequest(BaseModel):
    question: str | None = None
    word_limit: int | None = None


class CompanyScrapeRequest(BaseModel):
    url: str
    company_name: str


class PromptUpdate(BaseModel):
    content: str


# ============== Settings Endpoints ==============


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    settings_manager = get_settings_manager()
    return settings_manager.get_all(mask_api_key=True)


@router.put("/settings")
async def update_settings(data: AppSettingsUpdate) -> dict[str, Any]:
    settings_manager = get_settings_manager()
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return settings_manager.get_all(mask_api_key=True)
    settings_manager.update(updates)
    return settings_manager.get_all(mask_api_key=True)


@router.post("/settings/reset")
async def reset_settings() -> dict[str, Any]:
    settings_manager = get_settings_manager()
    settings_manager.reset_to_defaults()
    return settings_manager.get_all(mask_api_key=True)


# ============== Prompts Endpoints ==============

VALID_PROMPT_KEYS = [
    "resume_prompt",
    "cover_letter_prompt",
    "user_information",
    "resume_format",
    "application_question_prompt",
    "resume_prompt_zh",
    "cover_letter_prompt_zh",
    "user_information_zh",
    "resume_format_zh",
    "application_question_prompt_zh",
]


@router.get("/prompts")
async def get_prompts() -> dict[str, str]:
    prompt_manager = get_prompt_manager()
    return prompt_manager.get_all_prompts()


@router.get("/prompts/{prompt_key}")
async def get_prompt(prompt_key: str) -> dict[str, str]:
    if prompt_key not in VALID_PROMPT_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid prompt key. Valid: {VALID_PROMPT_KEYS}")
    prompt_manager = get_prompt_manager()
    content = prompt_manager.get_prompt(prompt_key)
    return {"key": prompt_key, "content": content}


@router.put("/prompts/{prompt_key}")
async def update_prompt(prompt_key: str, data: PromptUpdate) -> dict[str, Any]:
    if prompt_key not in VALID_PROMPT_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid prompt key. Valid: {VALID_PROMPT_KEYS}")

    prompt_manager = get_prompt_manager()

    # Validate placeholders
    warnings = prompt_manager.validate_prompt(prompt_key, data.content)

    success = prompt_manager.update_prompt(prompt_key, data.content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update prompt")

    result: dict[str, Any] = {
        "key": prompt_key,
        "content": data.content,
        "message": "Prompt updated successfully",
    }
    if warnings:
        result["warnings"] = warnings
    return result


@router.post("/prompts/reload")
async def reload_prompts() -> dict[str, str]:
    prompt_manager = get_prompt_manager()
    prompt_manager.reload_prompts()
    return {"message": "Prompts reloaded successfully"}


# ============== Provider Endpoints ==============


@router.get("/providers")
async def get_providers() -> list[dict]:
    from services.provider_registry import AVAILABLE_PROVIDERS

    return AVAILABLE_PROVIDERS


# ============== Template Endpoints ==============


@router.get("/templates")
async def get_templates() -> list[dict]:
    return task_manager.get_available_templates()


# ============== JD History Endpoints ==============


@router.get("/jd-history")
async def get_jd_history() -> list[dict]:
    return task_manager.get_jd_history()


# ============== Task Endpoints ==============


@router.post("/tasks", response_model=Task, dependencies=[Depends(require_api_key)])
@rate_limit(TASK_CREATE_RATE)
async def create_task(request: Request, task_data: TaskCreate):
    task = await task_manager.create_task(task_data)
    return task


@router.get("/tasks", response_model=list[Task])
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
    success = await task_manager.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or is currently running")
    return {"message": "Task deleted"}


@router.delete("/tasks")
async def delete_completed_tasks():
    count = await task_manager.delete_completed_tasks()
    return {"message": f"Deleted {count} tasks", "count": count}


@router.put("/tasks/{task_id}/job-description")
async def update_job_description(task_id: str, data: JobDescriptionUpdate):
    task = await task_manager.update_task_job_description(task_id, data.job_description)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or already started")
    return task


@router.put("/tasks/{task_id}/settings")
async def update_task_settings(task_id: str, data: TaskSettingsUpdate):
    task = await task_manager.update_task_settings(
        task_id,
        job_description=data.job_description,
        generate_cover_letter=data.generate_cover_letter,
        template_id=data.template_id,
        language=data.language,
        experience_level=data.experience_level,
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
    task = await task_manager.retry_task(task_id)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or cannot be retried")
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = await task_manager.cancel_task(task_id)
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


@router.get("/tasks/{task_id}/cover-letter-text")
async def get_cover_letter_text(task_id: str):
    """Get the raw cover letter text for copy-pasting."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.cover_letter_text:
        raise HTTPException(status_code=404, detail="Cover letter text not available")
    return {"text": task.cover_letter_text}


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
    tex_name = tex_name.replace('"', "").replace("\n", "").replace("\r", "")

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
    q = await task_manager.add_question(task_id, data.question, data.word_limit)
    if not q:
        raise HTTPException(status_code=404, detail="Task not found")
    return q


@router.put("/tasks/{task_id}/questions/{question_id}", response_model=ApplicationQuestion)
async def update_question(task_id: str, question_id: str, data: UpdateQuestionRequest):
    q = await task_manager.update_question(task_id, question_id, question=data.question, word_limit=data.word_limit)
    if not q:
        raise HTTPException(status_code=404, detail="Task or question not found")
    return q


@router.delete("/tasks/{task_id}/questions/{question_id}")
async def delete_question(task_id: str, question_id: str):
    success = await task_manager.delete_question(task_id, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task or question not found")
    return {"message": "Question deleted"}


# ============== Evaluation Endpoints ==============


def _extract_jd_analysis(task) -> dict | None:
    """Extract JD analysis from task's agent_outputs (v3 pipeline)."""
    outputs = getattr(task, "agent_outputs", None) or {}
    jd = outputs.get("jd_analyzer")
    if isinstance(jd, dict):
        return jd
    return None


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
        jd_analysis=_extract_jd_analysis(task),
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
        jd_analysis=_extract_jd_analysis(task),
        provider_name=task.provider or "gemini",
        task_id=task.id,
        task_number=task.task_number,
        use_llm_judge=True,
    )
    return result


# ============== Company Research (RAG) Endpoints ==============


@router.post("/companies/scrape", dependencies=[Depends(require_api_key)])
@rate_limit(SCRAPE_RATE)
async def scrape_company(request: Request, data: CompanyScrapeRequest):
    """Scrape a company website and index it for RAG retrieval."""
    validate_url_not_internal(data.url)
    try:
        from rag.retriever import scrape_and_index_company

        result = await scrape_and_index_company(data.url, data.company_name)
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="RAG module not installed (chromadb required)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e!s}")


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

    import asyncio

    pending_ids = [q.id for q in task.questions if q.status != "completed" or q.answer is None]
    await asyncio.gather(*(task_manager.generate_question_answer(task_id, qid) for qid in pending_ids))
    return task.questions
