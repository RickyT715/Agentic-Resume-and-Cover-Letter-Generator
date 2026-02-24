"""Rate limiting middleware using slowapi.

Applies per-client rate limits to prevent abuse.
Configurable via environment variables.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Default rate limits
DEFAULT_RATE = "60/minute"
TASK_CREATE_RATE = "10/minute"
SCRAPE_RATE = "5/minute"


def setup_rate_limiting(app: FastAPI):
    """Set up rate limiting on the FastAPI app.

    Gracefully skips if slowapi is not installed.
    """
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address
    except ImportError:
        logger.info("slowapi not installed, rate limiting disabled")
        return

    limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info(f"Rate limiting enabled: default={DEFAULT_RATE}")
