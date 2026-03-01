"""
Abstract base class for AI provider clients.
All providers (Gemini, Claude, OpenAI-compatible) extend this class.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


class AIClientBase(ABC):
    """Abstract base class for AI provider clients."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g. 'gemini', 'claude', 'openai_compat')."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the current model identifier."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        task_id: str = None,
        task_number: int = None,
        response_type: str = "general",
        **kwargs,
    ) -> str:
        """
        Send a prompt to the AI provider and return the response text.

        Args:
            prompt: The prompt to send
            task_id: Optional task ID for logging
            task_number: Optional task number for logging
            response_type: Type of response for file naming
            **kwargs: Provider-specific parameters

        Returns:
            Generated text response
        """
        ...

    # ---- Default high-level methods that delegate to generate() ----

    async def generate_resume(self, prompt: str, task_id: str = None, task_number: int = None) -> str:
        """Generate resume content."""
        logger.info(f"[{self.provider_name}] Generating resume for task {task_number}")
        return await self.generate(prompt, task_id=task_id, task_number=task_number, response_type="resume")

    async def generate_cover_letter(self, prompt: str, task_id: str = None, task_number: int = None) -> str:
        """Generate cover letter content."""
        logger.info(f"[{self.provider_name}] Generating cover letter for task {task_number}")
        return await self.generate(prompt, task_id=task_id, task_number=task_number, response_type="cover_letter")

    async def generate_question_answer(
        self,
        prompt: str,
        task_id: str = None,
        task_number: int = None,
        question_id: str = None,
    ) -> str:
        """Generate an answer to an application question."""
        logger.info(f"[{self.provider_name}] Generating question answer for task {task_number}, question {question_id}")
        return await self.generate(
            prompt,
            task_id=task_id,
            task_number=task_number,
            response_type=f"question_{question_id}",
        )

    async def generate_resume_with_error_feedback(
        self,
        prompt: str,
        error_log: str,
        previous_latex: str,
        task_id: str = None,
        task_number: int = None,
        attempt: int = 1,
    ) -> str:
        """Generate resume with error feedback from failed compilation."""
        logger.info(
            f"[{self.provider_name}] Regenerating resume with error feedback for task {task_number} (attempt {attempt})"
        )
        error_feedback_prompt = f"""{prompt}

IMPORTANT: The previous LaTeX generation failed to compile. Please fix the errors and generate valid LaTeX.

Previous LaTeX code that failed:
```latex
{previous_latex[:3000]}
```

Compilation error:
```
{error_log[:2000]}
```

Please generate corrected LaTeX code that will compile successfully. Focus on:
1. Fixing any syntax errors
2. Ensuring all packages are properly used
3. Matching all begin/end environments
4. Escaping special characters properly (%, &, $, #, _, etc.)
"""
        return await self.generate(
            error_feedback_prompt,
            task_id=task_id,
            task_number=task_number,
            response_type=f"resume_retry_attempt_{attempt}",
        )

    # ---- Shared response logging ----

    def _save_response(
        self,
        task_id: str,
        task_number: int,
        response_type: str,
        prompt: str,
        response: str,
        extra_metadata: str | None = None,
    ) -> Path | None:
        """
        Save AI response to a timestamped text file.

        Args:
            task_id: Unique task identifier
            task_number: Task number for easy identification
            response_type: Type of response (resume, cover_letter, etc.)
            prompt: The prompt sent
            response: The response received
            extra_metadata: Optional extra metadata string to append

        Returns:
            Path to the saved file, or None on failure
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"task_{task_number}_{response_type}_{timestamp}.txt"
        filepath = settings.responses_dir / filename

        extra_section = f"\n{extra_metadata}" if extra_metadata else ""

        content = f"""{"=" * 80}
{self.provider_name.upper()} API RESPONSE LOG
{"=" * 80}

Task ID: {task_id}
Task Number: {task_number}
Response Type: {response_type}
Provider: {self.provider_name}
Model: {self.model}
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{"=" * 80}
PROMPT
{"=" * 80}

{prompt}

{"=" * 80}
RESPONSE
{"=" * 80}

{response}
{extra_section}
{"=" * 80}
END OF LOG
{"=" * 80}
"""
        try:
            filepath.write_text(content, encoding="utf-8")
            logger.info(f"Saved {self.provider_name} response to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save {self.provider_name} response: {e}")
            return None
