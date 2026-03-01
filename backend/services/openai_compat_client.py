"""
OpenAI-compatible proxy AI provider client.
Works with Claude Code proxy, Ollama, LM Studio, and any OpenAI-compatible API.
"""

import asyncio
import logging
from datetime import datetime

from config import settings as app_settings
from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class OpenAICompatClient(AIClientBase):
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._client = None
        self._current_api_key = None
        self._current_base_url = None
        logger.info("OpenAICompatClient initialized (settings read dynamically per request)")

    def _get_client(self):
        """Get or create the OpenAI client, recreating if config changed."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is not installed. Run: pip install openai")

        api_key = (
            self.settings_manager.get("openai_compat_api_key")
            or getattr(app_settings, "openai_compat_api_key", "")
            or "not-needed"
        )
        base_url = (
            self.settings_manager.get("openai_compat_base_url")
            or getattr(app_settings, "openai_compat_base_url", "")
            or "http://localhost:3000/v1"
        )

        if self._client is None or self._current_api_key != api_key or self._current_base_url != base_url:
            self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
            self._current_api_key = api_key
            self._current_base_url = base_url
            logger.info(f"Created new OpenAI-compatible client (base_url={base_url})")

        return self._client

    @property
    def provider_name(self) -> str:
        return "openai_compat"

    @property
    def model(self) -> str:
        return (
            self.settings_manager.get("openai_compat_model")
            or getattr(app_settings, "openai_compat_model", "")
            or "gpt-4o"
        )

    @property
    def _temperature(self) -> float | None:
        return self.settings_manager.get("openai_compat_temperature")

    @property
    def _max_output_tokens(self) -> int | None:
        return self.settings_manager.get("openai_compat_max_output_tokens")

    async def generate(
        self,
        prompt: str,
        task_id: str = None,
        task_number: int = None,
        response_type: str = "general",
        **kwargs,
    ) -> str:
        base_url = self.settings_manager.get("openai_compat_base_url") or "http://localhost:3000/v1"
        logger.info(f"Sending request to OpenAI-compatible API (model={self.model}, base_url={base_url})")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            client = self._get_client()

            request_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }

            temp = self._temperature
            if temp is not None:
                request_kwargs["temperature"] = temp

            max_tokens = self._max_output_tokens
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens

            loop = asyncio.get_running_loop()
            start_time = datetime.now()

            response = await loop.run_in_executor(None, lambda: client.chat.completions.create(**request_kwargs))

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"OpenAI-compatible API response received in {elapsed:.2f} seconds")

            result = response.choices[0].message.content or ""
            logger.debug(f"Response length: {len(result)} characters")

            if task_id and task_number:
                self._save_response(
                    task_id=task_id,
                    task_number=task_number,
                    response_type=response_type,
                    prompt=prompt,
                    response=result,
                )

            return result

        except Exception as e:
            logger.error(f"OpenAI-compatible API error: {e}", exc_info=True)
            raise
