"""
Unit tests for rate limiting components
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.slowapi_limiter import get_client_ip, _is_valid_ip
from app.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.configs.app_config import settings


class TestGetClientIP:
    """Test IP extraction function."""

    def test_x_forwarded_for_single_ip(self):
        """Test X-Forwarded-For with single IP."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.1"

    def test_x_forwarded_for_multiple_ips(self):
        """Test X-Forwarded-For with proxy chain."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1, 203.0.113.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.1"  # First valid IP

    def test_x_real_ip(self):
        """Test X-Real-IP header."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "10.0.0.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "10.0.0.1"

    def test_cf_connecting_ip(self):
        """Test Cloudflare Connecting IP."""
        mock_request = MagicMock()
        mock_request.headers = {"CF-Connecting-IP": "203.0.113.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """Test fallback to client.host."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.100"

    def test_invalid_ip_fallback(self):
        """Test invalid IP in headers falls back."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "invalid.ip, 192.168.1.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.1"  # Next valid IP

    def test_no_valid_ip(self):
        """Test when no valid IP found."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "invalid.ip"}
        mock_request.client = None

        result = get_client_ip(mock_request)
        assert result == "127.0.0.1"


class TestIsValidIP:
    """Test IP validation function."""

    def test_valid_ipv4(self):
        assert _is_valid_ip("192.168.1.1") is True

    def test_valid_ipv6(self):
        assert _is_valid_ip("2001:db8::1") is True

    def test_invalid_ip(self):
        assert _is_valid_ip("invalid.ip") is False
        assert _is_valid_ip("999.999.999.999") is False


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.fixture
    def middleware(self):
        return RateLimitMiddleware(MagicMock())

    @pytest.fixture
    def mock_request(self):
        request = MagicMock()
        request.url.path = "/api/test"
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        return request

    @pytest.fixture
    def mock_response(self):
        return MagicMock()

    @patch('app.core.slowapi_limiter.limiter')
    async def test_exempt_route(self, mock_limiter, middleware, mock_request):
        """Test exempt routes bypass rate limiting."""
        mock_request.url.path = "/health"
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        assert response == mock_response
        mock_limiter.limiter.hit.assert_not_called()

    @patch('app.core.slowapi_limiter.limiter')
    async def test_rate_limit_allowed(self, mock_limiter, middleware, mock_request, mock_response):
        """Test request allowed when under limit."""
        mock_limiter.limiter.hit.return_value = True
        mock_limiter.limiter.get_window_stats.return_value = [95, 100, 1708617600]
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        mock_limiter.limiter.hit.assert_called_once_with("192.168.1.1", cost=1)
        # Check headers added
        assert mock_response.headers["X-RateLimit-Limit"] == str(settings.RATE_LIMIT_REQUESTS)
        assert mock_response.headers["X-RateLimit-Remaining"] == "95"
        assert mock_response.headers["X-RateLimit-Reset"] == "1708617600"

    @patch('app.core.slowapi_limiter.limiter')
    async def test_rate_limit_exceeded(self, mock_limiter, middleware, mock_request):
        """Test 429 response when rate limit exceeded."""
        mock_limiter.limiter.hit.return_value = False
        mock_limiter.limiter.get_window_stats.return_value = [0, 100, 1708617600 + 45]

        call_next = AsyncMock()
        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_not_called()
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        assert "RATE_LIMIT_EXCEEDED" in response.body.decode()
        assert response.headers["Retry-After"] == "45"

    @patch('app.core.slowapi_limiter.limiter')
    async def test_rate_limit_error_fallback(self, mock_limiter, middleware, mock_request, mock_response):
        """Test graceful fallback when rate limiter fails."""
        mock_limiter.limiter.hit.side_effect = Exception("Redis error")
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        assert response == mock_response
