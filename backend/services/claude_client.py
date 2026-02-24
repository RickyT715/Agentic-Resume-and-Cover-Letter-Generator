"""
Claude (Anthropic) AI provider client.
Uses the Anthropic SDK with run_in_executor for async compatibility.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager
from config import settings as app_settings

logger = logging.getLogger(__name__)


class ClaudeClient(AIClientBase):
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._client = None
        self._current_api_key = None
        logger.info("ClaudeClient initialized (settings read dynamically per request)")

    def _get_client(self):
        """Get or create the Anthropic client, recreating if API key changed."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is not installed. Run: pip install anthropic"
            )

        api_key = self.settings_manager.get("claude_api_key") or getattr(
            app_settings, "claude_api_key", ""
        )
        if not api_key:
            raise ValueError(
                "Claude API key not set. Configure it in Settings or .env file."
            )

        if self._client is None or self._current_api_key != api_key:
            self._client = anthropic.Anthropic(api_key=api_key)
            self._current_api_key = api_key
            logger.info("Created new Anthropic client")

        return self._client

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model(self) -> str:
        return (
            self.settings_manager.get("claude_model") or "claude-sonnet-4-5-20250929"
        )

    @property
    def _temperature(self) -> Optional[float]:
        return self.settings_manager.get("claude_temperature")

    @property
    def _max_output_tokens(self) -> int:
        return self.settings_manager.get("claude_max_output_tokens") or 16384

    @property
    def _extended_thinking(self) -> bool:
        return self.settings_manager.get("claude_extended_thinking") or False

    @property
    def _thinking_budget(self) -> int:
        return self.settings_manager.get("claude_thinking_budget") or 10000

    async def generate(
        self,
        prompt: str,
        task_id: str = None,
        task_number: int = None,
        response_type: str = "general",
        **kwargs,
    ) -> str:
        logger.info(
            f"Sending request to Claude API (model={self.model}, extended_thinking={self._extended_thinking})"
        )
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            client = self._get_client()

            # Build request kwargs
            request_kwargs = {
                "model": self.model,
                "max_tokens": self._max_output_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

            # Extended thinking and temperature are mutually exclusive in Claude
            if self._extended_thinking:
                request_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self._thinking_budget,
                }
                # temperature must be 1 when using extended thinking
                request_kwargs["temperature"] = 1
            else:
                temp = self._temperature
                if temp is not None:
                    request_kwargs["temperature"] = temp

            loop = asyncio.get_running_loop()
            start_time = datetime.now()

            response = await loop.run_in_executor(
                None, lambda: client.messages.create(**request_kwargs)
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Claude API response received in {elapsed:.2f} seconds")

            # Extract text from response content blocks
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)

            result = "\n".join(text_parts)
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
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise
