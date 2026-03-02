"""Finalize node: compiles LaTeX, creates PDFs, and produces final outputs."""

import asyncio
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from agents.state import ResumeState

logger = logging.getLogger(__name__)


async def compile_latex_node(state: ResumeState) -> dict:
    """Compile LaTeX source to PDF.

    Reads: latex_source, task_number, language, provider_name
    Writes: resume_pdf_path, current_node, agent_outputs
    """
    from config import settings
    from services.latex_compiler import LaTeXCompiler
    from services.latex_utils import process_latex_response
    from services.pdf_page_counter import validate_single_page
    from services.provider_registry import get_provider
    from services.settings_manager import get_settings_manager

    logger.info(f"Task {state['task_number']}: Compiling LaTeX to PDF")
    start = time.time()

    from services.latex_link_checker import fix_latex_links

    sm = get_settings_manager()
    enforce_one_page = sm.get("enforce_resume_one_page", True)
    max_page_retries = sm.get("max_page_retry_attempts", 3)

    compiler = LaTeXCompiler(max_retries=settings.max_latex_retries)
    current_latex = state["latex_source"]

    # Fix links before compilation
    current_latex = fix_latex_links(
        current_latex,
        sm.get("user_linkedin_url", ""),
        sm.get("user_github_url", ""),
    )

    # Validate resume contact info
    from services.prompt_manager import get_prompt_manager as _get_pm
    from services.resume_validator import validate_resume_async

    _pm = _get_pm()
    suffix = "_zh" if state.get("language") == "zh" else ""
    user_info_text = _pm.get_prompt(f"user_information{suffix}")
    current_latex, validation_warnings = await validate_resume_async(
        current_latex,
        user_info_text,
        state.get("language", "en"),
        sm,
        job_description=state.get("job_description", ""),
    )

    compiler_name = "xelatex" if state.get("language") == "zh" else "pdflatex"

    max_attempts = max(settings.max_latex_retries, max_page_retries)
    pdf_path = None

    for attempt in range(1, max_attempts + 1):
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            compiler.compile_once,
            current_latex,
            f"resume_task_{state['task_number']}",
            attempt,
            compiler_name,
        )

        if result.success:
            # Check page count if enforcement enabled
            if enforce_one_page and result.pdf_path:
                is_single, page_count = validate_single_page(result.pdf_path)
                if not is_single and page_count > 0 and attempt < max_attempts:
                    logger.warning(f"Task {state['task_number']}: Resume is {page_count} pages, retrying")
                    # Get AI to regenerate a shorter version
                    provider = get_provider(state["provider_name"])
                    from services.prompt_manager import get_prompt_manager

                    pm = get_prompt_manager()
                    resume_prompt = pm.get_resume_prompt_with_substitutions(
                        state["job_description"],
                        template_id=state.get("template_id", "classic"),
                        language=state.get("language", "en"),
                        enforce_one_page=enforce_one_page,
                        allow_fabrication=sm.get("allow_ai_fabrication", True),
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
                        raw = await provider.generate_resume_with_error_feedback(
                            resume_prompt,
                            page_feedback,
                            current_latex,
                            task_id=state["task_id"],
                            task_number=state["task_number"],
                            attempt=attempt + 1,
                        )
                        current_latex = process_latex_response(raw)
                        current_latex = fix_latex_links(
                            current_latex,
                            sm.get("user_linkedin_url", ""),
                            sm.get("user_github_url", ""),
                        )
                        current_latex, validation_warnings = await validate_resume_async(
                            current_latex,
                            user_info_text,
                            state.get("language", "en"),
                            sm,
                            skip_llm=True,
                        )
                        continue
                    except Exception as e:
                        logger.error(f"Task {state['task_number']}: Page-fix regen failed: {e}")

            pdf_path = str(result.pdf_path)
            break

        # Compilation failed - try to regenerate with error feedback
        if attempt < max_attempts:
            try:
                provider = get_provider(state["provider_name"])
                from services.prompt_manager import get_prompt_manager

                pm = get_prompt_manager()
                resume_prompt = pm.get_resume_prompt_with_substitutions(
                    state["job_description"],
                    template_id=state.get("template_id", "classic"),
                    language=state.get("language", "en"),
                    enforce_one_page=enforce_one_page,
                    allow_fabrication=sm.get("allow_ai_fabrication", True),
                )
                raw = await provider.generate_resume_with_error_feedback(
                    resume_prompt,
                    result.error_log or "Unknown compilation error",
                    current_latex,
                    task_id=state["task_id"],
                    task_number=state["task_number"],
                    attempt=attempt + 1,
                )
                current_latex = process_latex_response(raw)
                current_latex = fix_latex_links(
                    current_latex,
                    sm.get("user_linkedin_url", ""),
                    sm.get("user_github_url", ""),
                )
                current_latex, validation_warnings = await validate_resume_async(
                    current_latex,
                    user_info_text,
                    state.get("language", "en"),
                    sm,
                    skip_llm=True,
                )
            except Exception as e:
                logger.error(f"Task {state['task_number']}: LaTeX regen failed: {e}")

    latency = int((time.time() - start) * 1000)

    if not pdf_path:
        error_msg = f"LaTeX compilation failed after {max_attempts} attempts"
        logger.error(f"Task {state['task_number']}: {error_msg}")
        return {
            "error": error_msg,
            "latex_source": current_latex,
            "current_node": "compile_latex",
        }

    logger.info(f"Task {state['task_number']}: LaTeX compiled successfully, latency={latency}ms")

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["compile_latex"] = {"latency_ms": latency}
    if validation_warnings:
        agent_outputs["validation_warnings"] = validation_warnings

    return {
        "resume_pdf_path": pdf_path,
        "latex_source": current_latex,
        "current_node": "compile_latex",
        "agent_outputs": agent_outputs,
    }


async def extract_text_node(state: ResumeState) -> dict:
    """Extract text from compiled resume PDF for cover letter context.

    Reads: resume_pdf_path
    Writes: resume_text, current_node
    """
    from services.pdf_extractor import PDFTextExtractor

    logger.info(f"Task {state['task_number']}: Extracting text from resume PDF")

    extractor = PDFTextExtractor()
    resume_text = extractor.extract(state["resume_pdf_path"])

    logger.info(f"Task {state['task_number']}: Extracted {len(resume_text)} chars from PDF")

    return {
        "resume_text": resume_text,
        "current_node": "extract_text",
    }


async def create_cover_letter_pdf_node(state: ResumeState) -> dict:
    """Create cover letter PDF from text.

    Reads: cover_letter_text, company_name, position_name, task_number
    Writes: cover_letter_pdf_path, current_node, agent_outputs
    """
    from config import settings
    from services.settings_manager import get_settings_manager
    from services.text_to_pdf import TextToPDFConverter

    logger.info(f"Task {state['task_number']}: Creating cover letter PDF")
    start = time.time()

    sm = get_settings_manager()
    sm.get("enforce_cover_letter_one_page", True)

    converter = TextToPDFConverter()

    # Build filename
    company = state.get("company_name", "")
    position = state.get("position_name", "")
    if company and position:
        label = f"{company}_{position}"
    elif company:
        label = company
    else:
        label = "Cover_Letter"
    safe_label = _sanitize_filename(label)

    # Generate PDF
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = settings.output_dir / f"cover_letter_{safe_label}.pdf"
    if pdf_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = settings.output_dir / f"cover_letter_{safe_label}_{timestamp}.pdf"

    converter.convert(state["cover_letter_text"], pdf_path)

    latency = int((time.time() - start) * 1000)
    logger.info(f"Task {state['task_number']}: Cover letter PDF created, latency={latency}ms")

    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["create_cover_pdf"] = {"latency_ms": latency}

    return {
        "cover_letter_pdf_path": str(pdf_path),
        "current_node": "create_cover_pdf",
        "agent_outputs": agent_outputs,
    }


async def finalize_node(state: ResumeState) -> dict:
    """Finalize: copy resume PDF to final location with proper name.

    Reads: resume_pdf_path, company_name, position_name, task_number
    Writes: resume_pdf_path (updated), current_node
    """
    from config import settings

    logger.info(f"Task {state['task_number']}: Finalizing outputs")

    # If there's an error or no resume PDF, skip file operations
    if state.get("error") or not state.get("resume_pdf_path"):
        logger.warning(f"Task {state['task_number']}: Finalizing with error or no resume PDF")
        return {
            "current_node": "finalize",
        }

    company = state.get("company_name", "")
    position = state.get("position_name", "")
    if company and position:
        label = f"{company}_{position}"
    elif company:
        label = company
    else:
        label = "Resume"
    safe_label = _sanitize_filename(label)

    # Copy resume to final location
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    final_path = settings.output_dir / f"resume_{safe_label}.pdf"
    if final_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = settings.output_dir / f"resume_{safe_label}_{timestamp}.pdf"

    src = Path(state["resume_pdf_path"])
    if src.exists():
        shutil.copy(src, final_path)

    logger.info(f"Task {state['task_number']}: Resume saved to {final_path}")

    return {
        "resume_pdf_path": str(final_path),
        "current_node": "finalize",
    }


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    safe = re.sub(r"[\s\-]+", "_", name)
    safe = re.sub(r'[<>:"/\\|?*]', "", safe)
    safe = re.sub(r"[^\w.]", "_", safe)
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("_")
    if len(safe) > 50:
        safe = safe[:50].rstrip("_")
    return safe or "Unknown"
