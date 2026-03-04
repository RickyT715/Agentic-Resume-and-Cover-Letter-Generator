"""Unit tests for rate limiting configuration and behavior."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRateLimitConstants:
    def test_default_rate_value(self):
        """DEFAULT_RATE should be '60/minute'."""
        from middleware.rate_limit import DEFAULT_RATE

        assert DEFAULT_RATE == "60/minute"

    def test_task_create_rate_value(self):
        """TASK_CREATE_RATE should be '60/minute'."""
        from middleware.rate_limit import TASK_CREATE_RATE

        assert TASK_CREATE_RATE == "60/minute"

    def test_scrape_rate_value(self):
        """SCRAPE_RATE should be '5/minute'."""
        from middleware.rate_limit import SCRAPE_RATE

        assert SCRAPE_RATE == "5/minute"


class TestRateLimitFunction:
    def test_rate_limit_returns_callable(self):
        """rate_limit() should return a callable (a decorator)."""
        from middleware.rate_limit import rate_limit

        decorator = rate_limit("10/minute")
        assert callable(decorator)

    def test_noop_decorator_wraps_function(self):
        """When slowapi is not available, rate_limit returns a no-op decorator."""
        from unittest.mock import patch

        with patch("middleware.rate_limit._slowapi_available", False), patch("middleware.rate_limit.limiter", None):
            from middleware.rate_limit import rate_limit

            decorator = rate_limit("5/minute")
            assert callable(decorator)

            # The decorator should wrap an async function transparently
            async def dummy_endpoint():
                return "ok"

            wrapped = decorator(dummy_endpoint)
            assert callable(wrapped)

    @pytest.mark.asyncio
    async def test_noop_decorator_passes_through(self):
        """No-op decorator should call through to the original function."""
        from middleware.rate_limit import _noop_limit

        decorator = _noop_limit("10/minute")

        async def my_handler():
            return "result"

        wrapped = decorator(my_handler)
        result = await wrapped()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_noop_decorator_passes_args(self):
        """No-op decorator should forward args and kwargs to the wrapped function."""
        from middleware.rate_limit import _noop_limit

        decorator = _noop_limit("10/minute")

        async def my_handler(x, y=0):
            return x + y

        wrapped = decorator(my_handler)
        result = await wrapped(3, y=4)
        assert result == 7
