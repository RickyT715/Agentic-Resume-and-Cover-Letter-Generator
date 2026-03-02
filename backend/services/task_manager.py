import asyncio
import json
import logging
import re
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from config import settings
from models.task import ApplicationQuestion, QuestionStatus, Task, TaskCreate, TaskStatus, TaskStep
from services.latex_compiler import CompilationAttempt, CompilationError, LaTeXCompiler
from services.latex_link_checker import fix_latex_links
from services.latex_utils import extract_metadata, process_latex_response
from services.pdf_extractor import PDFTextExtractor
from services.pdf_page_counter import validate_single_page
from services.prompt_manager import get_prompt_manager
from services.provider_registry import get_provider_for_task
from services.resume_validator import validate_resume_async
from services.settings_manager import get_settings_manager
from services.text_to_pdf import TextToPDFConverter

logger = logging.getLogger(__name__)

TASKS_FILE = settings.data_dir / "tasks.json"
JD_HISTORY_FILE = settings.data_dir / "jd_history.json"


class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.tasks: dict[str, Task] = {}
        self.task_counter = 0
        self._progress_callbacks: list[Callable] = []
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)

        # Initialize services
        logger.info("Initializing TaskManager services...")
        self.settings_manager = get_settings_manager()
        self.prompt_manager = get_prompt_manager()
        self.latex_compiler = LaTeXCompiler(max_retries=settings.max_latex_retries)
        self.pdf_extractor = PDFTextExtractor()
        self.text_to_pdf = TextToPDFConverter()

        # Load persisted tasks
        self._load_tasks()
        logger.info("TaskManager initialized successfully")

    # ===================== Persistence =====================

    def _load_tasks(self):
        """Load tasks from disk on startup."""
        if not TASKS_FILE.exists():
            return
        try:
            data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            for task_data in data.get("tasks", []):
                task = Task(**task_data)
                # Reset running tasks to failed (server restarted mid-run)
                if task.status in (TaskStatus.RUNNING, TaskStatus.QUEUED):
                    task.status = TaskStatus.FAILED
                    task.error_message = "Server restarted while task was running"
                    for step in task.steps:
                        if step.status == TaskStatus.RUNNING:
                            step.status = TaskStatus.FAILED
                            step.message = "Interrupted by server restart"
                self.tasks[task.id] = task
            self.task_counter = data.get("task_counter", 0)
            logger.info(f"Loaded {len(self.tasks)} tasks from disk")
        except Exception as e:
            logger.error(f"Failed to load tasks from disk: {e}")

    def _save_tasks(self):
        """Persist tasks to disk."""
        try:
            data = {
                "task_counter": self.task_counter,
                "tasks": [task.model_dump(mode="json") for task in self.tasks.values()],
            }
            TASKS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    # ===================== JD History =====================

    def _save_jd_to_history(self, job_description: str):
        """Save a job description to the history file."""
        if not job_description.strip():
            return
        try:
            history = self._load_jd_history()
            # Avoid duplicates - remove existing if present, add to front
            history = [jd for jd in history if jd.get("text") != job_description]
            history.insert(
                0,
                {
                    "text": job_description,
                    "preview": job_description[:120].replace("\n", " "),
                    "saved_at": datetime.now().isoformat(),
                },
            )
            # Keep last 20
            history = history[:20]
            JD_HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save JD history: {e}")

    def _load_jd_history(self) -> list:
        if not JD_HISTORY_FILE.exists():
            return []
        try:
            return json.loads(JD_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def get_jd_history(self) -> list:
        return self._load_jd_history()

    # ===================== Callbacks =====================

    def register_progress_callback(self, callback: Callable):
        self._progress_callbacks.append(callback)

    async def _notify_progress(
        self,
        task: Task,
        step: TaskStep,
        status: TaskStatus,
        message: str = "",
        attempt: int = 0,
    ):
        """Notify all registered callbacks of progress."""
        update = {
            "task_id": task.id,
            "task_number": task.task_number,
            "step": step.value,
            "status": status.value,
            "message": message,
            "attempt": attempt,
        }

        for step_progress in task.steps:
            if step_progress.step == step:
                step_progress.status = status
                step_progress.message = message
                step_progress.attempt = attempt
                if status == TaskStatus.RUNNING:
                    step_progress.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    step_progress.completed_at = datetime.now()

        log_level = logging.ERROR if status == TaskStatus.FAILED else logging.INFO
        logger.log(log_level, f"Task {task.task_number} [{task.id}] - {step.value}: {status.value} - {message}")

        self._save_tasks()

        for callback in self._progress_callbacks:
            try:
                await callback(update)
            except Exception as e:
                logger.error(f"Progress callback error: {e}", exc_info=True)

    # ===================== CRUD =====================

    def create_task(self, task_data: TaskCreate) -> Task:
        self.task_counter += 1

        generate_cover_letter = task_data.generate_cover_letter
        if generate_cover_letter is None:
            generate_cover_letter = self.settings_manager.get("generate_cover_letter", True)

        template_id = task_data.template_id or self.settings_manager.get("default_template_id", "classic")

        experience_level = task_data.experience_level
        if not experience_level or experience_level == "auto":
            saved_level = self.settings_manager.get("default_experience_level", "auto")
            if isinstance(saved_level, str) and saved_level not in ("", "auto"):
                experience_level = saved_level

        task = Task(
            task_number=self.task_counter,
            job_description=task_data.job_description,
            generate_cover_letter=generate_cover_letter,
            template_id=template_id,
            language=task_data.language,
            experience_level=experience_level,
            provider=task_data.provider,
        )
        self.tasks[task.id] = task
        self._save_tasks()
        logger.info(f"Created task {task.task_number} [{task.id}]")
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        return list(self.tasks.values())

    def delete_task(self, task_id: str) -> bool:
        """Delete a task and its output files."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.status == TaskStatus.RUNNING:
            return False

        # Clean up files
        for path_str in [task.resume_pdf_path, task.cover_letter_pdf_path]:
            if path_str:
                p = Path(path_str)
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete file {p}: {e}")

        del self.tasks[task_id]
        self._save_tasks()
        logger.info(f"Deleted task {task.task_number} [{task_id}]")
        return True

    def delete_completed_tasks(self) -> int:
        """Delete all completed tasks. Returns count deleted."""
        to_delete = [
            tid
            for tid, t in self.tasks.items()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        for tid in to_delete:
            self.delete_task(tid)
        return len(to_delete)

    def retry_task(self, task_id: str) -> Task | None:
        """Reset a failed/cancelled/completed task to pending so it can be re-run."""
        task = self.tasks.get(task_id)
        if not task or task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.COMPLETED):
            return None

        task.status = TaskStatus.PENDING
        task.error_message = None
        task.cancelled = False
        task.failed_latex_attempts = []
        task.resume_pdf_path = None
        task.cover_letter_pdf_path = None
        task.latex_source = None
        task.completed_at = None
        task._rebuild_steps()
        self._save_tasks()
        logger.info(f"Reset task {task.task_number} [{task_id}] to pending for retry")
        return task

    def cancel_task(self, task_id: str) -> Task | None:
        """Mark a task for cancellation."""
        task = self.tasks.get(task_id)
        if not task or task.status not in (TaskStatus.RUNNING, TaskStatus.QUEUED, TaskStatus.PENDING):
            return None
        task.cancelled = True
        if task.status == TaskStatus.PENDING or task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            for step in task.steps:
                if step.status == TaskStatus.PENDING:
                    step.status = TaskStatus.CANCELLED
        self._save_tasks()
        logger.info(f"Cancellation requested for task {task.task_number} [{task_id}]")
        return task

    def update_task_job_description(self, task_id: str, job_description: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.job_description = job_description
            self._save_tasks()
            return task
        return None

    def update_task_settings(
        self,
        task_id: str,
        job_description: str | None = None,
        generate_cover_letter: bool | None = None,
        template_id: str | None = None,
        language: str | None = None,
        experience_level: str | None = None,
        provider: str | None = None,
    ) -> Task | None:
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            if job_description is not None:
                task.job_description = job_description
            if template_id is not None:
                task.template_id = template_id
            if generate_cover_letter is not None:
                task.generate_cover_letter = generate_cover_letter
                task._rebuild_steps()
            if language is not None:
                task.language = language
            if experience_level is not None:
                task.experience_level = experience_level
            if provider is not None:
                task.provider = provider if provider != "" else None
            self._save_tasks()
            return task
        return None

    # ===================== Questions =====================

    def add_question(self, task_id: str, question: str, word_limit: int = 150) -> ApplicationQuestion | None:
        """Add an application question to a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        q = ApplicationQuestion(question=question, word_limit=word_limit)
        task.questions.append(q)
        self._save_tasks()
        logger.info(f"Added question {q.id} to task {task.task_number}")
        return q

    def update_question(
        self, task_id: str, question_id: str, question: str | None = None, word_limit: int | None = None
    ) -> ApplicationQuestion | None:
        """Update a question's text or word limit. Resets answer if question text changed."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        for q in task.questions:
            if q.id == question_id:
                if question is not None and question != q.question:
                    q.question = question
                    q.answer = None
                    q.status = QuestionStatus.PENDING
                    q.error_message = None
                    q.answered_at = None
                if word_limit is not None:
                    q.word_limit = word_limit
                self._save_tasks()
                return q
        return None

    def delete_question(self, task_id: str, question_id: str) -> bool:
        """Delete a question from a task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        original_len = len(task.questions)
        task.questions = [q for q in task.questions if q.id != question_id]
        if len(task.questions) < original_len:
            self._save_tasks()
            logger.info(f"Deleted question {question_id} from task {task.task_number}")
            return True
        return False

    async def generate_question_answer(self, task_id: str, question_id: str) -> ApplicationQuestion | None:
        """Generate an answer for a single application question."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        target_q = None
        for q in task.questions:
            if q.id == question_id:
                target_q = q
                break
        if not target_q:
            return None

        target_q.status = QuestionStatus.RUNNING
        target_q.error_message = None
        self._save_tasks()

        try:
            ai_client = get_provider_for_task(task.provider)
            allow_fabrication = self.settings_manager.get("allow_ai_fabrication", True)
            prompt = self.prompt_manager.get_question_prompt_with_substitutions(
                question=target_q.question,
                job_description=task.job_description,
                word_limit=target_q.word_limit,
                language=task.language,
                allow_fabrication=allow_fabrication,
            )
            answer = await ai_client.generate_question_answer(
                prompt, task_id=task.id, task_number=task.task_number, question_id=target_q.id
            )
            target_q.answer = answer.strip()
            target_q.status = QuestionStatus.COMPLETED
            target_q.answered_at = datetime.now()
            self._save_tasks()
            logger.info(f"Generated answer for question {question_id} on task {task.task_number}")
            return target_q
        except Exception as e:
            target_q.status = QuestionStatus.FAILED
            target_q.error_message = str(e)
            self._save_tasks()
            logger.error(f"Failed to generate answer for question {question_id}: {e}")
            return target_q

    # ===================== Templates =====================

    def get_available_templates(self) -> list[dict]:
        """Return list of available resume templates."""
        templates = [
            {
                "id": "classic",
                "name": "Classic",
                "description": "Traditional single-column resume with clean formatting",
            },
            {"id": "modern", "name": "Modern", "description": "Two-column layout with a skills sidebar"},
            {"id": "minimal", "name": "Minimal", "description": "Clean, spacious design with minimal styling"},
        ]
        return templates

    # ===================== Task Execution =====================

    async def run_task(self, task_id: str):
        """Run a task with concurrency limiting (v2 pipeline)."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.QUEUED
        self._save_tasks()

        # Broadcast queued status
        await self._notify_progress(task, task.steps[0].step, TaskStatus.PENDING, "Waiting in queue...")

        async with self._semaphore:
            if task.cancelled:
                task.status = TaskStatus.CANCELLED
                self._save_tasks()
                return
            await self._execute_task(task_id)

    async def run_task_v3(self, task_id: str):
        """Run a task using the v3 LangGraph multi-agent pipeline."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.QUEUED
        task.pipeline_version = "v3"
        self._save_tasks()

        await self._notify_progress(task, task.steps[0].step, TaskStatus.PENDING, "Waiting in queue (v3 pipeline)...")

        async with self._semaphore:
            if task.cancelled:
                task.status = TaskStatus.CANCELLED
                self._save_tasks()
                return

            from services.langgraph_executor import run_langgraph_pipeline

            # Save JD to history
            self._save_jd_to_history(task.job_description)

            # Build a progress callback that broadcasts via WebSocket
            async def v3_progress_callback(update: dict):
                for cb in self._progress_callbacks:
                    try:
                        await cb(update)
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")

            await run_langgraph_pipeline(task, progress_callback=v3_progress_callback)
            self._save_tasks()

    async def _execute_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.RUNNING
        start_time = datetime.now()

        # Resolve AI provider for this task
        ai_client = get_provider_for_task(task.provider)
        provider_label = f"{ai_client.provider_name}/{ai_client.model}"

        enforce_resume_one_page = self.settings_manager.get("enforce_resume_one_page", True)
        enforce_cover_letter_one_page = self.settings_manager.get("enforce_cover_letter_one_page", True)
        max_page_retry_attempts = self.settings_manager.get("max_page_retry_attempts", 3)
        allow_fabrication = self.settings_manager.get("allow_ai_fabrication", True)

        logger.info(f"{'=' * 60}")
        logger.info(f"Starting task {task.task_number} [{task_id}]")
        logger.info(f"Provider: {provider_label}")
        logger.info(f"Generate cover letter: {task.generate_cover_letter}")
        logger.info(f"Template: {task.template_id}")
        logger.info(f"{'=' * 60}")

        # Save JD to history
        self._save_jd_to_history(task.job_description)

        resume_pdf_path = None
        cover_letter_pdf_path = None
        latex_code = None

        try:
            # ---- Step 1: Generate Resume ----
            self._check_cancelled(task)
            await self._notify_progress(
                task,
                TaskStep.GENERATE_RESUME,
                TaskStatus.RUNNING,
                f"Generating resume with {provider_label}...",
            )

            resume_prompt = self.prompt_manager.get_resume_prompt_with_substitutions(
                task.job_description,
                template_id=task.template_id,
                language=task.language,
                experience_level=task.experience_level,
                enforce_one_page=enforce_resume_one_page,
                allow_fabrication=allow_fabrication,
            )
            raw_response = await ai_client.generate_resume(resume_prompt, task_id=task.id, task_number=task.task_number)
            # Extract company/position metadata before stripping to \documentclass
            metadata = extract_metadata(raw_response)
            if metadata["company_name"]:
                task.company_name = metadata["company_name"]
            if metadata["position_name"]:
                task.position_name = metadata["position_name"]

            latex_code = process_latex_response(raw_response)
            latex_code = fix_latex_links(
                latex_code,
                self.settings_manager.get("user_linkedin_url", ""),
                self.settings_manager.get("user_github_url", ""),
            )

            # Validate resume contact info
            suffix = "_zh" if task.language == "zh" else ""
            user_info_text = self.prompt_manager.get_prompt(f"user_information{suffix}")
            latex_code, validation_warnings = await validate_resume_async(
                latex_code,
                user_info_text,
                task.language,
                self.settings_manager,
                ai_client,
                job_description=task.job_description,
            )
            task.validation_warnings = validation_warnings

            task.latex_source = latex_code
            await self._notify_progress(
                task,
                TaskStep.GENERATE_RESUME,
                TaskStatus.COMPLETED,
                "Resume LaTeX generated",
            )

            # ---- Step 2: Compile LaTeX ----
            self._check_cancelled(task)
            await self._notify_progress(
                task,
                TaskStep.COMPILE_LATEX,
                TaskStatus.RUNNING,
                "Compiling LaTeX to PDF...",
            )

            resume_pdf_path = await self._compile_latex_with_retry_and_page_check(
                task,
                latex_code,
                enforce_resume_one_page,
                max_page_retry_attempts,
                ai_client,
                user_info_text=user_info_text,
            )

            await self._notify_progress(task, TaskStep.COMPILE_LATEX, TaskStatus.COMPLETED, "Resume PDF created")

        except _TaskCancelled:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self._save_tasks()
            await self._broadcast_cancel(task)
            return
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()

            # Preserve partial resume result if it exists
            if resume_pdf_path:
                final_path = self._get_unique_output_path("resume_partial", ".pdf")
                shutil.copy(resume_pdf_path, final_path)
                task.resume_pdf_path = str(final_path)

            logger.error(f"Task {task.task_number} FAILED after {elapsed:.2f}s: {e}", exc_info=True)
            for step in task.steps:
                if step.status == TaskStatus.RUNNING:
                    step.status = TaskStatus.FAILED
                    step.message = str(e)
                    await self._notify_progress(task, step.step, TaskStatus.FAILED, str(e))
            self._save_tasks()
            return

        # Build file name from metadata (company + position) or fallback
        if task.company_name and task.position_name:
            file_label = f"{task.company_name}_{task.position_name}"
        elif task.company_name:
            file_label = task.company_name
        else:
            file_label = "Resume"
        safe_company_name = self._sanitize_filename(file_label)

        # ---- Cover Letter Steps (if enabled) ----
        if task.generate_cover_letter:
            try:
                # Step 3: Extract Text
                self._check_cancelled(task)
                await self._notify_progress(
                    task,
                    TaskStep.EXTRACT_TEXT,
                    TaskStatus.RUNNING,
                    "Extracting text from PDF...",
                )
                resume_text = self.pdf_extractor.extract(resume_pdf_path)
                await self._notify_progress(
                    task,
                    TaskStep.EXTRACT_TEXT,
                    TaskStatus.COMPLETED,
                    f"Extracted {len(resume_text)} characters",
                )

                # Step 4: Generate Cover Letter
                self._check_cancelled(task)
                await self._notify_progress(
                    task,
                    TaskStep.GENERATE_COVER_LETTER,
                    TaskStatus.RUNNING,
                    f"Generating cover letter with {provider_label}...",
                )
                cover_letter_prompt = self.prompt_manager.get_cover_letter_prompt_with_substitutions(
                    resume_text, task.job_description, language=task.language, allow_fabrication=allow_fabrication
                )
                cover_letter_text = await ai_client.generate_cover_letter(
                    cover_letter_prompt, task_id=task.id, task_number=task.task_number
                )
                task.cover_letter_text = cover_letter_text
                # Use cover letter heuristic as fallback if metadata didn't provide a name
                if not task.company_name:
                    task.company_name = self._extract_company_name(cover_letter_text)
                    if task.company_name and task.position_name:
                        file_label = f"{task.company_name}_{task.position_name}"
                    elif task.company_name:
                        file_label = task.company_name
                    safe_company_name = self._sanitize_filename(file_label if task.company_name else "Resume")
                await self._notify_progress(
                    task,
                    TaskStep.GENERATE_COVER_LETTER,
                    TaskStatus.COMPLETED,
                    "Cover letter generated",
                )

                # Step 5: Create Cover Letter PDF
                self._check_cancelled(task)
                await self._notify_progress(
                    task,
                    TaskStep.CREATE_COVER_PDF,
                    TaskStatus.RUNNING,
                    "Creating cover letter PDF...",
                )
                cover_letter_pdf_path = await self._create_cover_letter_with_page_check(
                    task,
                    cover_letter_text,
                    resume_text,
                    safe_company_name,
                    enforce_cover_letter_one_page,
                    max_page_retry_attempts,
                    ai_client,
                )
                await self._notify_progress(
                    task,
                    TaskStep.CREATE_COVER_PDF,
                    TaskStatus.COMPLETED,
                    "Cover letter PDF created",
                )

            except _TaskCancelled:
                # Still save the resume result before cancelling
                final_path = self._get_unique_output_path(f"resume_{safe_company_name}", ".pdf")
                shutil.copy(resume_pdf_path, final_path)
                task.resume_pdf_path = str(final_path)
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self._save_tasks()
                await self._broadcast_cancel(task)
                return
            except Exception as e:
                # Cover letter failed, but resume succeeded - save partial result
                logger.error(f"Task {task.task_number}: Cover letter failed: {e}", exc_info=True)
                final_path = self._get_unique_output_path(f"resume_{safe_company_name}", ".pdf")
                shutil.copy(resume_pdf_path, final_path)
                task.resume_pdf_path = str(final_path)
                task.status = TaskStatus.FAILED
                task.error_message = f"Cover letter generation failed: {e}. Resume is still available."
                task.completed_at = datetime.now()

                for step in task.steps:
                    if step.status == TaskStatus.RUNNING:
                        step.status = TaskStatus.FAILED
                        step.message = str(e)
                        await self._notify_progress(task, step.step, TaskStatus.FAILED, str(e))
                self._save_tasks()
                return

        # ---- Finalize ----
        final_resume_path = self._get_unique_output_path(f"resume_{safe_company_name}", ".pdf")
        shutil.copy(resume_pdf_path, final_resume_path)

        task.resume_pdf_path = str(final_resume_path)
        if cover_letter_pdf_path:
            task.cover_letter_pdf_path = str(cover_letter_pdf_path)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Task {task.task_number} COMPLETED in {elapsed:.2f}s")
        self._save_tasks()

        final_step = TaskStep.CREATE_COVER_PDF if task.generate_cover_letter else TaskStep.COMPILE_LATEX
        await self._notify_progress(
            task,
            final_step,
            TaskStatus.COMPLETED,
            "All files generated successfully",
        )

    # ===================== Cancellation =====================

    def _check_cancelled(self, task: Task):
        if task.cancelled:
            raise _TaskCancelled()

    async def _broadcast_cancel(self, task: Task):
        for step in task.steps:
            if step.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                step.status = TaskStatus.CANCELLED
                step.message = "Task cancelled"
        await self._notify_progress(task, task.steps[0].step, TaskStatus.CANCELLED, "Task cancelled by user")

    # ===================== LaTeX Compilation =====================

    async def _compile_latex_with_retry_and_page_check(
        self,
        task: Task,
        initial_latex: str,
        enforce_one_page: bool,
        max_page_retries: int,
        ai_client=None,
        user_info_text: str = "",
    ):
        self.latex_compiler.clear_attempts()
        current_latex = initial_latex
        max_attempts = max(settings.max_latex_retries, max_page_retries)

        for attempt in range(1, max_attempts + 1):
            self._check_cancelled(task)

            await self._notify_progress(
                task,
                TaskStep.COMPILE_LATEX,
                TaskStatus.RUNNING,
                f"Compilation attempt {attempt}/{max_attempts}" + (" (with feedback)" if attempt > 1 else ""),
                attempt=attempt,
            )

            compiler = "xelatex" if task.language == "zh" else "pdflatex"
            loop = asyncio.get_running_loop()
            result: CompilationAttempt = await loop.run_in_executor(
                None,
                self.latex_compiler.compile_once,
                current_latex,
                f"resume_task_{task.task_number}",
                attempt,
                compiler,
            )

            result.used_error_feedback = attempt > 1
            self.latex_compiler.add_attempt(result)

            if result.success:
                if enforce_one_page and result.pdf_path:
                    is_single_page, page_count = validate_single_page(result.pdf_path)

                    if not is_single_page and page_count > 0:
                        logger.warning(f"Task {task.task_number}: Resume has {page_count} pages")

                        if attempt < max_attempts:
                            await self._notify_progress(
                                task,
                                TaskStep.COMPILE_LATEX,
                                TaskStatus.RUNNING,
                                f"Resume is {page_count} pages. Regenerating to fit 1 page...",
                                attempt=attempt,
                            )
                            page_feedback = (
                                f"\nThe resume compiled successfully but is {page_count} pages long. "
                                "It MUST be exactly 1 page. Please:\n"
                                "1. Remove less important bullet points\n"
                                "2. Condense descriptions\n"
                                "3. Use shorter phrases\n"
                                "4. Remove less relevant experiences/projects\n"
                                "5. Reduce spacing if possible\n\n"
                                "Generate a new version that fits exactly 1 page.\n"
                            )
                            try:
                                allow_fabrication = self.settings_manager.get("allow_ai_fabrication", True)
                                resume_prompt = self.prompt_manager.get_resume_prompt_with_substitutions(
                                    task.job_description,
                                    template_id=task.template_id,
                                    language=task.language,
                                    enforce_one_page=enforce_one_page,
                                    allow_fabrication=allow_fabrication,
                                )
                                raw = await ai_client.generate_resume_with_error_feedback(
                                    resume_prompt,
                                    page_feedback,
                                    current_latex,
                                    task_id=task.id,
                                    task_number=task.task_number,
                                    attempt=attempt + 1,
                                )
                                current_latex = process_latex_response(raw)
                                current_latex = fix_latex_links(
                                    current_latex,
                                    self.settings_manager.get("user_linkedin_url", ""),
                                    self.settings_manager.get("user_github_url", ""),
                                )
                                current_latex, retry_warnings = await validate_resume_async(
                                    current_latex,
                                    user_info_text,
                                    task.language,
                                    self.settings_manager,
                                    skip_llm=True,
                                )
                                task.validation_warnings = retry_warnings
                                task.latex_source = current_latex
                                continue
                            except Exception as e:
                                logger.error(f"Task {task.task_number}: Page-fix regen failed: {e}")
                        else:
                            logger.warning(f"Task {task.task_number}: Accepting {page_count}-page resume")

                task.latex_source = current_latex
                return result.pdf_path

            last_error = result.error_log

            if attempt < max_attempts:
                await self._notify_progress(
                    task,
                    TaskStep.COMPILE_LATEX,
                    TaskStatus.RUNNING,
                    "Regenerating LaTeX with error feedback...",
                    attempt=attempt,
                )
                try:
                    allow_fabrication = self.settings_manager.get("allow_ai_fabrication", True)
                    resume_prompt = self.prompt_manager.get_resume_prompt_with_substitutions(
                        task.job_description,
                        template_id=task.template_id,
                        language=task.language,
                        enforce_one_page=enforce_one_page,
                        allow_fabrication=allow_fabrication,
                    )
                    raw = await ai_client.generate_resume_with_error_feedback(
                        resume_prompt,
                        last_error,
                        current_latex,
                        task_id=task.id,
                        task_number=task.task_number,
                        attempt=attempt + 1,
                    )
                    current_latex = process_latex_response(raw)
                    current_latex = fix_latex_links(
                        current_latex,
                        self.settings_manager.get("user_linkedin_url", ""),
                        self.settings_manager.get("user_github_url", ""),
                    )
                    current_latex, retry_warnings = await validate_resume_async(
                        current_latex,
                        user_info_text,
                        task.language,
                        self.settings_manager,
                        skip_llm=True,
                    )
                    task.validation_warnings = retry_warnings
                    task.latex_source = current_latex
                except Exception as e:
                    logger.error(f"Task {task.task_number}: Regen failed: {e}")

        task.failed_latex_attempts = [a.latex_code for a in self.latex_compiler.attempts]
        raise CompilationError(
            f"LaTeX compilation failed after {max_attempts} attempts",
            self.latex_compiler.attempts,
        )

    async def _create_cover_letter_with_page_check(
        self,
        task: Task,
        cover_letter_text: str,
        resume_text: str,
        safe_company_name: str,
        enforce_one_page: bool,
        max_retries: int,
        ai_client=None,
    ):
        current_text = cover_letter_text

        for attempt in range(1, max_retries + 1):
            self._check_cancelled(task)

            cover_letter_pdf_path = self._get_unique_output_path(f"cover_letter_{safe_company_name}", ".pdf")
            self.text_to_pdf.convert(current_text, cover_letter_pdf_path)

            if enforce_one_page:
                is_single_page, page_count = validate_single_page(cover_letter_pdf_path)

                if not is_single_page and page_count > 0 and attempt < max_retries:
                    await self._notify_progress(
                        task,
                        TaskStep.CREATE_COVER_PDF,
                        TaskStatus.RUNNING,
                        f"Cover letter is {page_count} pages. Regenerating shorter...",
                    )
                    page_feedback_prompt = self.prompt_manager.get_cover_letter_prompt_with_substitutions(
                        resume_text, task.job_description, language=task.language
                    )
                    page_feedback_prompt += (
                        f"\n\nIMPORTANT: The previous cover letter was {page_count} pages. "
                        "It MUST be exactly 1 page. Write a more concise version."
                    )
                    try:
                        current_text = await ai_client.generate_cover_letter(
                            page_feedback_prompt, task_id=task.id, task_number=task.task_number
                        )
                        continue
                    except Exception as e:
                        logger.error(f"Cover letter regen failed: {e}")

            return cover_letter_pdf_path

        return cover_letter_pdf_path

    # ===================== Utilities =====================

    def _get_unique_output_path(self, base_name: str, extension: str):
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        target = settings.output_dir / f"{base_name}{extension}"
        if not target.exists():
            return target
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return settings.output_dir / f"{base_name}_{timestamp}{extension}"

    def _extract_company_name(self, cover_letter_text: str) -> str:
        lines = cover_letter_text.strip().split("\n")
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        if len(non_empty_lines) >= 6:
            company_name = non_empty_lines[5].strip()
            if not company_name.lower().startswith("dear") and len(company_name) < 100:
                return company_name

        found_date = False
        for line in non_empty_lines:
            line = line.strip()
            if re.search(
                r"\d{4}|January|February|March|April|May|June|July|August|September|October|November|December",
                line,
                re.IGNORECASE,
            ):
                found_date = True
                continue
            if found_date:
                if any(
                    title in line.lower() for title in ["hiring manager", "recruiter", "hr ", "human resources", "dear"]
                ):
                    continue
                if re.search(r"\b[A-Z]{2}\b|,\s*[A-Z]{2}\s*\d{5}", line):
                    continue
                if 2 < len(line) < 100:
                    return line

        return "Unknown_Company"

    def _sanitize_filename(self, name: str) -> str:
        safe_name = re.sub(r"[\s\-]+", "_", name)
        safe_name = re.sub(r'[<>:"/\\|?*]', "", safe_name)
        safe_name = re.sub(r"[^\w\.]", "_", safe_name)
        safe_name = re.sub(r"_+", "_", safe_name)
        safe_name = safe_name.strip("_")
        if len(safe_name) > 50:
            safe_name = safe_name[:50].rstrip("_")
        return safe_name or "Unknown_Company"


class _TaskCancelled(Exception):
    """Internal exception for task cancellation flow."""

    pass


# Singleton instance
task_manager = TaskManager()
