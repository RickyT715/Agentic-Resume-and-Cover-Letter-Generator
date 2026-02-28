import subprocess
import tempfile
import shutil
from pathlib import Path
import logging
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CompilationAttempt:
    attempt_number: int
    latex_code: str
    success: bool
    error_log: Optional[str] = None
    pdf_path: Optional[Path] = None
    used_error_feedback: bool = False


class CompilationError(Exception):
    def __init__(self, message: str, attempts: List[CompilationAttempt]):
        super().__init__(message)
        self.attempts = attempts

    def get_debug_report(self) -> str:
        """Generate a human-readable report of all failed attempts."""
        report = ["=" * 60, "LATEX COMPILATION FAILURE REPORT", "=" * 60]

        for attempt in self.attempts:
            report.append(f"\n--- Attempt {attempt.attempt_number} ---")
            report.append(f"Success: {attempt.success}")
            report.append(f"Used Error Feedback: {attempt.used_error_feedback}")
            report.append(f"\nLaTeX Code (first 2000 chars):\n{attempt.latex_code[:2000]}")
            if attempt.error_log:
                report.append(f"\nError Log (first 1000 chars):\n{attempt.error_log[:1000]}")

        return "\n".join(report)


class LaTeXCompiler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.attempts: List[CompilationAttempt] = []

    def compile_once(
        self, latex_code: str, output_filename: str, attempt_num: int, compiler: str = "pdflatex"
    ) -> CompilationAttempt:
        """Single compilation attempt. Returns CompilationAttempt with results."""
        from config import settings
        
        # Log what we're about to compile
        logger.info(f"LaTeX compilation attempt {attempt_num} for {output_filename}")
        logger.debug(f"LaTeX code length: {len(latex_code)} characters")
        logger.debug(f"LaTeX starts with: {latex_code[:100]!r}")
        logger.debug(f"LaTeX ends with: {latex_code[-100:]!r}")
        
        # Validate the LaTeX code before compilation
        if not latex_code.strip().startswith("\\documentclass"):
            logger.error(f"LaTeX code does not start with \\documentclass!")
            logger.error(f"First 200 chars: {latex_code[:200]!r}")
            return CompilationAttempt(
                attempt_number=attempt_num,
                latex_code=latex_code,
                success=False,
                error_log="LaTeX code does not start with \\documentclass. Extraction may have failed.",
            )
        
        if not latex_code.strip().endswith("\\end{document}"):
            logger.error("LaTeX code does not end with \\end{document}!")
            logger.error(f"Last 200 chars: {latex_code[-200:]!r}")
            return CompilationAttempt(
                attempt_number=attempt_num,
                latex_code=latex_code,
                success=False,
                error_log="LaTeX code does not end with \\end{document}. Extraction may have failed.",
            )
        
        # Save the LaTeX to a debug file for inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_tex_file = settings.logs_dir / f"debug_{output_filename}_attempt_{attempt_num}_{timestamp}.tex"
        try:
            debug_tex_file.write_text(latex_code, encoding="utf-8")
            logger.info(f"Saved debug LaTeX file: {debug_tex_file}")
        except Exception as e:
            logger.warning(f"Could not save debug LaTeX file: {e}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / f"{output_filename}.tex"
            pdf_file = temp_path / f"{output_filename}.pdf"
            log_file = temp_path / f"{output_filename}.log"

            # Write LaTeX file
            tex_file.write_text(latex_code, encoding="utf-8")
            logger.debug(f"Wrote LaTeX to temp file: {tex_file}")

            # Run compiler (twice for references/formatting)
            try:
                for pass_num in range(2):  # Two passes for proper formatting
                    logger.debug(f"Running {compiler} pass {pass_num + 1}")
                    result = subprocess.run(
                        [
                            compiler,
                            "-interaction=nonstopmode",
                            "-halt-on-error",
                            f"-output-directory={temp_dir}",
                            str(tex_file),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    logger.debug(f"{compiler} pass {pass_num + 1} return code: {result.returncode}")

                # Check if PDF was created
                if pdf_file.exists():
                    logger.info(f"PDF created successfully: {pdf_file}")
                    # Copy PDF to a persistent location before temp dir cleanup
                    persistent_pdf = settings.output_dir / f"{output_filename}_attempt_{attempt_num}.pdf"
                    shutil.copy(pdf_file, persistent_pdf)
                    logger.info(f"Copied PDF to: {persistent_pdf}")

                    return CompilationAttempt(
                        attempt_number=attempt_num,
                        latex_code=latex_code,
                        success=True,
                        pdf_path=persistent_pdf,
                    )
                else:
                    logger.error("PDF file was not created")
                    error_log = ""
                    if log_file.exists():
                        error_log = log_file.read_text(encoding="utf-8", errors="ignore")
                        logger.error(f"LaTeX log file contents (last 2000 chars):\n{error_log[-2000:]}")
                    else:
                        error_log = result.stdout + "\n" + result.stderr
                        logger.error(f"pdflatex output:\n{error_log}")
                    
                    # Save error log for debugging
                    error_log_file = settings.logs_dir / f"latex_error_{output_filename}_attempt_{attempt_num}_{timestamp}.log"
                    try:
                        error_log_file.write_text(error_log, encoding="utf-8")
                        logger.info(f"Saved error log: {error_log_file}")
                    except Exception as e:
                        logger.warning(f"Could not save error log file: {e}")

                    return CompilationAttempt(
                        attempt_number=attempt_num,
                        latex_code=latex_code,
                        success=False,
                        error_log=error_log,
                    )

            except subprocess.TimeoutExpired:
                logger.error(f"{compiler} timed out after 60 seconds")
                return CompilationAttempt(
                    attempt_number=attempt_num,
                    latex_code=latex_code,
                    success=False,
                    error_log=f"Compilation timed out after 60 seconds",
                )
            except FileNotFoundError:
                logger.error(f"{compiler} not found - is texlive installed?")
                return CompilationAttempt(
                    attempt_number=attempt_num,
                    latex_code=latex_code,
                    success=False,
                    error_log=f"{compiler} not found. Please install texlive",
                )
            except Exception as e:
                logger.error(f"Unexpected error during compilation: {e}", exc_info=True)
                return CompilationAttempt(
                    attempt_number=attempt_num,
                    latex_code=latex_code,
                    success=False,
                    error_log=str(e),
                )

    def get_last_error(self) -> Optional[str]:
        """Get the error log from the last failed attempt."""
        if self.attempts and not self.attempts[-1].success:
            return self.attempts[-1].error_log
        return None

    def get_last_latex(self) -> Optional[str]:
        """Get the LaTeX code from the last attempt."""
        if self.attempts:
            return self.attempts[-1].latex_code
        return None

    def clear_attempts(self):
        """Clear the attempts history."""
        self.attempts = []

    def add_attempt(self, attempt: CompilationAttempt):
        """Add an attempt to the history."""
        self.attempts.append(attempt)
