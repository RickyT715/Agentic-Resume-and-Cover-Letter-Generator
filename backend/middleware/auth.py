"""Optional API key authentication middleware.

If settings.api_auth_key is empty, auth is disabled (dev mode).
Otherwise, all write endpoints require a valid X-API-Key header.
"""

from fastapi import Header, HTTPException
from fastapi.security import APIKeyHeader

from config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """FastAPI dependency: enforce API key when api_auth_key is configured."""
    if not settings.api_auth_key:
        return
    if not x_api_key or x_api_key != settings.api_auth_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
