"""Unit tests for API key authentication middleware."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from middleware.auth import require_api_key


def _make_app():
    """Build a minimal FastAPI app with the require_api_key dependency."""
    from fastapi import Depends

    app = FastAPI()

    @app.get("/protected")
    async def protected_route(key: None = Depends(require_api_key)):
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
class TestAuthMiddleware:
    async def test_no_auth_key_configured_passes_without_header(self):
        """When api_auth_key is empty, all requests pass without any header."""
        app = _make_app()
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.api_auth_key = ""
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/protected")
        assert r.status_code == 200

    async def test_auth_key_configured_missing_header_returns_401(self):
        """When api_auth_key is set, requests without X-API-Key header get 401."""
        app = _make_app()
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.api_auth_key = "secret-key"
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/protected")
        assert r.status_code == 401

    async def test_auth_key_configured_wrong_key_returns_401(self):
        """When api_auth_key is set, requests with wrong key get 401."""
        app = _make_app()
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.api_auth_key = "secret-key"
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    async def test_auth_key_configured_correct_key_passes(self):
        """When api_auth_key is set, requests with correct X-API-Key header pass."""
        app = _make_app()
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.api_auth_key = "secret-key"
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/protected", headers={"X-API-Key": "secret-key"})
        assert r.status_code == 200

    async def test_empty_string_api_key_in_header_rejected(self):
        """When api_auth_key is set, an empty X-API-Key header should be rejected."""
        app = _make_app()
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.api_auth_key = "secret-key"
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/protected", headers={"X-API-Key": ""})
        assert r.status_code == 401
