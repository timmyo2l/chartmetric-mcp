# tests/test_auth.py
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from chartmetric_mcp.auth import TokenManager, AuthError


def test_raises_if_api_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(AuthError, match="CHARTMETRIC_API_KEY"):
            TokenManager()


def test_fetches_token_on_first_call(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "test-token-123"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        token = mgr.get_token()

    assert token == "test-token-123"
    mock_httpx_post.assert_called_once_with(
        "https://api.chartmetric.com/api/token",
        json={"refreshtoken": "my-api-key"},
        timeout=10,
    )


def test_caches_token_within_expiry(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "cached-token"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        token1 = mgr.get_token()
        token2 = mgr.get_token()

    assert token1 == token2
    assert mock_httpx_post.call_count == 1  # only fetched once


def test_refreshes_when_near_expiry(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "new-token"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        mgr._token = "old-token"
        mgr._expires_at = time.time() + 200  # < 5 min remaining
        token = mgr.get_token()

    assert token == "new-token"


def test_raises_on_401_from_token_endpoint(mock_httpx_post):
    mock_httpx_post.return_value.status_code = 401

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "bad-key"}):
        mgr = TokenManager()
        with pytest.raises(AuthError, match="invalid or expired"):
            mgr.get_token()


@pytest.fixture
def mock_httpx_post():
    with patch("chartmetric_mcp.auth.httpx.post") as mock:
        yield mock
