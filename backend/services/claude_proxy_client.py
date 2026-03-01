"""
Claude Code Proxy AI provider client.
Uses the Anthropic SDK pointed at a local proxy (e.g. claude-code-proxy)
that exposes the Anthropic Messages API on a configurable base URL.

Uses streaming mode to avoid truncated-response issues common with proxies.
"""

import asyncio
import logging
from datetime import datetime

from config import settings as app_settings
from services.ai_client_base import AIClientBase
from services.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class ClaudeProxyClient(AIClientBase):
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._client = None
        self._current_api_key = None
        self._current_base_url = None
        self.last_token_usage = None  # Token usage from the most recent API call
        logger.info("ClaudeProxyClient initialized (settings read dynamically per request)")

    def _get_client(self):
        """Get or create the Anthropic client, recreating if settings changed."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is not installed. Run: pip install anthropic")

        api_key = (
            self.settings_manager.get("claude_proxy_api_key")
            or getattr(app_settings, "claude_proxy_api_key", "")
            or "not-needed"
        )

        base_url = self.settings_manager.get("claude_proxy_base_url") or getattr(
            app_settings, "claude_proxy_base_url", "http://localhost:42069"
        )

        if self._client is None or self._current_api_key != api_key or self._current_base_url != base_url:
            self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
            self._current_api_key = api_key
            self._current_base_url = base_url
            logger.info(f"Created new Anthropic proxy client (base_url={base_url})")

        return self._client

    @property
    def provider_name(self) -> str:
        return "claude_proxy"

    @property
    def model(self) -> str:
        return self.settings_manager.get("claude_proxy_model") or "claude-sonnet-4-5-20250929"

    @property
    def _temperature(self) -> float | None:
        return self.settings_manager.get("claude_proxy_temperature")

    @property
    def _max_output_tokens(self) -> int:
        return self.settings_manager.get("claude_proxy_max_output_tokens") or 16384

    async def generate(
        self,
        prompt: str,
        task_id: str | None = None,
        task_number: int | None = None,
        response_type: str = "general",
        **kwargs,
    ) -> str:
        logger.info(f"Sending request to Claude Proxy (model={self.model}, streaming=true)")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            client = self._get_client()

            request_kwargs = {
                "model": self.model,
                "max_tokens": self._max_output_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

            temp = self._temperature
            if temp is not None:
                request_kwargs["temperature"] = temp

            loop = asyncio.get_running_loop()
            start_time = datetime.now()

            # Use streaming to avoid truncated-response JSON parse errors.
            # Proxies sometimes truncate large buffered responses; SSE streaming
            # assembles the full message from small incremental events instead.
            def _stream_call():
                with client.messages.stream(**request_kwargs) as stream:
                    return stream.get_final_message()

            response = await loop.run_in_executor(None, _stream_call)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Claude Proxy response received in {elapsed:.2f} seconds")

            # Extract token usage from response
            usage = getattr(response, "usage", None)
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
                total_tokens = input_tokens + output_tokens
                logger.info(f"Token usage: input={input_tokens}, output={output_tokens}, total={total_tokens}")
                self.last_token_usage = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
            else:
                self.last_token_usage = None

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
            logger.error(f"Claude Proxy API error: {e}", exc_info=True)
            raise
