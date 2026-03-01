import asyncio
import logging
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from config import settings
from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class GeminiClient(AIClientBase):
    def __init__(self):
        """Initialize client. Settings are read dynamically for each request."""
        self.settings_manager = get_settings_manager()
        self._client = None
        self._current_api_key = None
        self.last_token_usage = None  # Token usage from the most recent API call
        logger.info("GeminiClient initialized (settings read dynamically per request)")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _get_client(self):
        """Get or create the Gemini client, recreating if API key changed."""
        api_key = self.settings_manager.get("gemini_api_key") or settings.gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Configure it in Settings or .env file.")

        # Recreate client if API key changed
        if self._client is None or self._current_api_key != api_key:
            self._client = genai.Client(api_key=api_key)
            self._current_api_key = api_key
            logger.info("Created new Gemini client")

        return self._client

    @property
    def model(self):
        """Get current model from settings."""
        return self.settings_manager.get("gemini_model") or settings.gemini_model

    @property
    def default_temperature(self):
        return self.settings_manager.get("gemini_temperature")

    @property
    def default_top_k(self):
        return self.settings_manager.get("gemini_top_k")

    @property
    def default_top_p(self):
        return self.settings_manager.get("gemini_top_p")

    @property
    def default_max_output_tokens(self):
        return self.settings_manager.get("gemini_max_output_tokens")

    @property
    def default_thinking_level(self):
        return self.settings_manager.get("gemini_thinking_level") or "high"

    @property
    def default_enable_search(self):
        return self.settings_manager.get("gemini_enable_search") or False

    def _save_gemini_response(
        self,
        task_id: str,
        task_number: int,
        response_type: str,
        prompt: str,
        response: str,
        grounding_metadata: dict | None = None,
    ) -> Path:
        """Save Gemini API response, including optional grounding metadata."""
        extra_metadata = None
        if grounding_metadata:
            extra_metadata = f"""{"=" * 80}
GROUNDING METADATA (Google Search)
{"=" * 80}

Search Queries: {grounding_metadata.get("web_search_queries", [])}

Sources:
{self._format_grounding_chunks(grounding_metadata.get("grounding_chunks", []))}

Generation Parameters:
  - Temperature: {self.default_temperature or "default"}
  - Top-K: {self.default_top_k or "default"}
  - Top-P: {self.default_top_p or "default"}
  - Thinking Level: {self.default_thinking_level}
  - Search Grounding: enabled"""
        else:
            extra_metadata = f"""Generation Parameters:
  - Temperature: {self.default_temperature or "default"}
  - Top-K: {self.default_top_k or "default"}
  - Top-P: {self.default_top_p or "default"}
  - Thinking Level: {self.default_thinking_level}
  - Search Grounding: disabled"""

        return self._save_response(
            task_id=task_id,
            task_number=task_number,
            response_type=response_type,
            prompt=prompt,
            response=response,
            extra_metadata=extra_metadata,
        )

    def _format_grounding_chunks(self, chunks: list) -> str:
        """Format grounding chunks for logging."""
        if not chunks:
            return "  None"

        formatted = []
        for i, chunk in enumerate(chunks, 1):
            if hasattr(chunk, "web"):
                formatted.append(f"  {i}. {chunk.web.title}: {chunk.web.uri}")
            elif isinstance(chunk, dict) and "web" in chunk:
                formatted.append(f"  {i}. {chunk['web'].get('title', 'N/A')}: {chunk['web'].get('uri', 'N/A')}")

        return "\n".join(formatted) if formatted else "  None"

    def _build_config(
        self,
        thinking_level: str | None = None,
        enable_search: bool | None = None,
        temperature: float | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
    ) -> types.GenerateContentConfig:
        """
        Build generation config with all parameters.

        Args:
            thinking_level: Override default thinking level ("minimal", "low", "medium", "high")
            enable_search: Override default search grounding setting
            temperature: Override default temperature (0.0 - 2.0)
            top_k: Override default top_k (1 - 100)
            top_p: Override default top_p (0.0 - 1.0)
            max_output_tokens: Override default max output tokens

        Returns:
            GenerateContentConfig object
        """
        # Use provided values or fall back to defaults
        thinking = thinking_level or self.default_thinking_level
        search = enable_search if enable_search is not None else self.default_enable_search
        temp = temperature if temperature is not None else self.default_temperature
        k = top_k if top_k is not None else self.default_top_k
        p = top_p if top_p is not None else self.default_top_p
        max_tokens = max_output_tokens if max_output_tokens is not None else self.default_max_output_tokens

        # Build config dictionary
        config_kwargs = {}

        # Add thinking config for Gemini 3.x models
        # Gemini 3/3.1 Pro use thinking_level enum; thinking cannot be turned off
        # Gemini 3.1 Pro adds MEDIUM level; Gemini 3 Pro supports LOW and HIGH only
        if "gemini-3" in self.model.lower():
            level_str = (thinking or "high").lower()
            level_map = {
                "low": types.ThinkingLevel.LOW,
                "high": types.ThinkingLevel.HIGH,
            }
            # Map unsupported levels to closest available
            if level_str == "minimal":
                level_str = "low"
            elif level_str == "medium":
                level_str = "high"
            thinking_enum = level_map.get(level_str, types.ThinkingLevel.HIGH)

            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_enum)
            logger.debug(f"Thinking level '{thinking_enum}' enabled for {self.model}")

        # Add tools (Google Search)
        if search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
            logger.debug("Google Search grounding enabled")

        # Add generation parameters (only if explicitly set)
        if temp is not None:
            config_kwargs["temperature"] = temp
        if k is not None:
            config_kwargs["top_k"] = k
        if p is not None:
            config_kwargs["top_p"] = p
        if max_tokens is not None:
            config_kwargs["max_output_tokens"] = max_tokens

        return types.GenerateContentConfig(**config_kwargs)

    def _extract_grounding_metadata(self, response) -> dict | None:
        """Extract grounding metadata from response if available."""
        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    return {
                        "web_search_queries": getattr(metadata, "web_search_queries", []),
                        "grounding_chunks": getattr(metadata, "grounding_chunks", []),
                        "search_entry_point": getattr(metadata, "search_entry_point", None),
                    }
        except Exception as e:
            logger.debug(f"Could not extract grounding metadata: {e}")
        return None

    async def generate(
        self,
        prompt: str,
        thinking_level: str | None = None,
        enable_search: bool | None = None,
        temperature: float | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        task_id: str | None = None,
        task_number: int | None = None,
        response_type: str = "general",
    ) -> str:
        """
        Send prompt to Gemini and return response text.

        Args:
            prompt: The prompt to send
            thinking_level: "none", "low", "medium", or "high" (default from config)
            enable_search: Enable Google Search grounding (default from config)
            temperature: Temperature for generation (default from config)
            top_k: Top-K sampling (default from config)
            top_p: Top-P (nucleus) sampling (default from config)
            max_output_tokens: Maximum output tokens (default from config)
            task_id: Optional task ID for logging
            task_number: Optional task number for logging
            response_type: Type of response for file naming

        Returns:
            Generated text response
        """
        effective_thinking = thinking_level or self.default_thinking_level
        effective_search = enable_search if enable_search is not None else self.default_enable_search

        logger.info(
            f"Sending request to Gemini API (model={self.model}, thinking_level={effective_thinking}, search={effective_search})"
        )
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            # Get client (creates new one if API key changed)
            client = self._get_client()

            # Build configuration
            config = self._build_config(
                thinking_level=thinking_level,
                enable_search=enable_search,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_output_tokens=max_output_tokens,
            )

            # Run the synchronous API call in a thread pool
            loop = asyncio.get_running_loop()
            start_time = datetime.now()

            current_model = self.model  # Capture current model for lambda
            response = await loop.run_in_executor(
                None, lambda: client.models.generate_content(model=current_model, contents=prompt, config=config)
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Gemini API response received in {elapsed_time:.2f} seconds")
            logger.debug(f"Response length: {len(response.text)} characters")

            # Extract token usage from response
            usage = getattr(response, "usage_metadata", None)
            if usage:
                input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                total_tokens = getattr(usage, "total_token_count", 0) or 0
                logger.info(f"Token usage: input={input_tokens}, output={output_tokens}, total={total_tokens}")
                # Store on client for callers to access
                self.last_token_usage = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
            else:
                self.last_token_usage = None

            # Extract grounding metadata if search was enabled
            grounding_metadata = None
            if effective_search:
                grounding_metadata = self._extract_grounding_metadata(response)
                if grounding_metadata and grounding_metadata.get("web_search_queries"):
                    logger.info(f"Search queries used: {grounding_metadata['web_search_queries']}")

            # Save response to file if task info provided
            if task_id and task_number:
                self._save_gemini_response(
                    task_id=task_id,
                    task_number=task_number,
                    response_type=response_type,
                    prompt=prompt,
                    response=response.text,
                    grounding_metadata=grounding_metadata,
                )

            return response.text

        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise

    async def generate_resume(self, prompt: str, task_id: str | None = None, task_number: int | None = None) -> str:
        """Generate resume with high thinking level for complex formatting."""
        logger.info(f"[gemini] Generating resume for task {task_number}")
        return await self.generate(
            prompt,
            thinking_level="high",
            enable_search=False,
            task_id=task_id,
            task_number=task_number,
            response_type="resume",
        )

    async def generate_cover_letter(
        self, prompt: str, task_id: str | None = None, task_number: int | None = None
    ) -> str:
        """Generate cover letter with high thinking level."""
        logger.info(f"[gemini] Generating cover letter for task {task_number}")
        return await self.generate(
            prompt, thinking_level="high", task_id=task_id, task_number=task_number, response_type="cover_letter"
        )

    async def generate_question_answer(
        self, prompt: str, task_id: str | None = None, task_number: int | None = None, question_id: str | None = None
    ) -> str:
        """Generate an answer to an application question with low thinking level."""
        logger.info(f"[gemini] Generating question answer for task {task_number}, question {question_id}")
        return await self.generate(
            prompt,
            thinking_level="low",
            enable_search=False,
            task_id=task_id,
            task_number=task_number,
            response_type=f"question_{question_id}",
        )

    async def generate_resume_with_error_feedback(
        self,
        prompt: str,
        error_log: str,
        previous_latex: str,
        task_id: str | None = None,
        task_number: int | None = None,
        attempt: int = 1,
    ) -> str:
        """Generate resume with error feedback from failed compilation."""
        logger.info(f"[gemini] Regenerating resume with error feedback for task {task_number} (attempt {attempt})")

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
            thinking_level="high",
            enable_search=False,
            task_id=task_id,
            task_number=task_number,
            response_type=f"resume_retry_attempt_{attempt}",
        )
