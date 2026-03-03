"""Rate limiting middleware using slowapi.

Applies per-client rate limits to prevent abuse.
Configurable via environment variables.
"""

import logging
from functools import wraps
from typing import Any

from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Default rate limits
DEFAULT_RATE = "60/minute"
TASK_CREATE_RATE = "10/minute"
SCRAPE_RATE = "5/minute"


def _noop_limit(_rate: str) -> Any:
    """No-op decorator used when slowapi is not installed."""

    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


_slowapi_available = False
limiter: Any = None

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE])
    _slowapi_available = True
except ImportError:
    pass


def rate_limit(rate: str) -> Any:
    """Decorator: apply rate limit if slowapi is available, else no-op."""
    if _slowapi_available and limiter is not None:
        return limiter.limit(rate)
    return _noop_limit(rate)


def setup_rate_limiting(app: FastAPI) -> None:
    """Register the limiter and error handler on the FastAPI app.

    Gracefully skips if slowapi is not installed.
    """
    if not _slowapi_available or limiter is None:
        logger.info("slowapi not installed, rate limiting disabled")
        return

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )

    logger.info(f"Rate limiting enabled: default={DEFAULT_RATE}")
