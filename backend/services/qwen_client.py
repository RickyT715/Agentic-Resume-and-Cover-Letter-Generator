"""
Qwen (Alibaba Cloud) AI provider client.
Uses the OpenAI-compatible DashScope API.
"""

import asyncio
import logging
from datetime import datetime

from config import settings as app_settings
from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class QwenClient(AIClientBase):
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._client = None
        self._current_api_key = None
        logger.info("QwenClient initialized (settings read dynamically per request)")

    def _get_client(self):
        """Get or create the OpenAI client pointing at DashScope."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is not installed. Run: pip install openai")

        api_key = (
            self.settings_manager.get("qwen_api_key")
            or getattr(app_settings, "qwen_api_key", "")
            or "not-needed"
        )

        if self._client is None or self._current_api_key != api_key:
            self._client = openai.OpenAI(
                api_key=api_key,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            )
            self._current_api_key = api_key
            logger.info("Created new Qwen client")

        return self._client

    @property
    def provider_name(self) -> str:
        return "qwen"

    @property
    def model(self) -> str:
        return (
            self.settings_manager.get("qwen_model")
            or getattr(app_settings, "qwen_model", "")
            or "qwen-plus"
        )

    @property
    def _temperature(self) -> float | None:
        return self.settings_manager.get("qwen_temperature")

    @property
    def _max_output_tokens(self) -> int | None:
        return self.settings_manager.get("qwen_max_output_tokens")

    async def generate(
        self,
        prompt: str,
        task_id: str | None = None,
        task_number: int | None = None,
        response_type: str = "general",
        **kwargs,
    ) -> str:
        logger.info(f"Sending request to Qwen API (model={self.model})")
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

            response = await loop.run_in_executor(
                None, lambda: client.chat.completions.create(**request_kwargs)
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Qwen API response received in {elapsed:.2f} seconds")

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
            logger.error(f"Qwen API error: {e}", exc_info=True)
            raise
