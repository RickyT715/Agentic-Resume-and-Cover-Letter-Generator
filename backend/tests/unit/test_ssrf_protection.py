"""Unit tests for SSRF URL validation in api/routes.py."""

import socket
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.routes import validate_url_not_internal


def _mock_dns(ip: str):
    """Return a context manager that mocks socket.getaddrinfo to return a given IP."""
    return patch(
        "api.routes.socket.getaddrinfo",
        return_value=[(None, None, None, None, (ip, 0))],
    )


class TestSSRFProtection:
    def test_public_url_passes(self):
        """A public URL resolving to a non-private IP should not raise."""
        with _mock_dns("142.250.80.46"):  # google.com-like IP
            # Should not raise
            validate_url_not_internal("https://www.google.com")

    def test_localhost_127_rejected(self):
        """http://127.0.0.1 should be rejected."""
        with _mock_dns("127.0.0.1"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://127.0.0.1")
        assert exc_info.value.status_code == 400

    def test_private_10_network_rejected(self):
        """http://10.0.0.1 should be rejected."""
        with _mock_dns("10.0.0.1"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://10.0.0.1")
        assert exc_info.value.status_code == 400

    def test_private_172_16_network_rejected(self):
        """http://172.16.0.1 should be rejected."""
        with _mock_dns("172.16.0.1"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://172.16.0.1")
        assert exc_info.value.status_code == 400

    def test_private_192_168_network_rejected(self):
        """http://192.168.1.1 should be rejected."""
        with _mock_dns("192.168.1.1"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://192.168.1.1")
        assert exc_info.value.status_code == 400

    def test_link_local_169_254_rejected(self):
        """http://169.254.169.254 (AWS metadata) should be rejected."""
        with _mock_dns("169.254.169.254"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://169.254.169.254")
        assert exc_info.value.status_code == 400

    def test_ftp_scheme_rejected(self):
        """ftp://example.com should be rejected (non-http/https scheme)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("ftp://example.com")
        assert exc_info.value.status_code == 400

    def test_file_scheme_rejected(self):
        """file:///etc/passwd should be rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("file:///etc/passwd")
        assert exc_info.value.status_code == 400

    def test_localhost_name_rejected(self):
        """http://localhost should be rejected (resolves to 127.0.0.1)."""
        with _mock_dns("127.0.0.1"), pytest.raises(HTTPException) as exc_info:
            validate_url_not_internal("http://localhost")
        assert exc_info.value.status_code == 400

    def test_unresolvable_hostname_rejected(self):
        """A hostname that cannot be resolved should raise HTTPException."""
        with (
            patch("api.routes.socket.getaddrinfo", side_effect=socket.gaierror("Name not resolved")),
            pytest.raises(HTTPException) as exc_info,
        ):
            validate_url_not_internal("http://this.hostname.does.not.exist.invalid")
        assert exc_info.value.status_code == 400

    def test_https_public_url_passes(self):
        """https:// scheme with a public IP should be allowed."""
        with _mock_dns("8.8.8.8"):  # Google DNS public IP
            # Should not raise
            validate_url_not_internal("https://dns.google.com")
