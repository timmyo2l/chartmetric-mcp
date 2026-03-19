# tests/test_client.py
import pytest
from unittest.mock import patch, MagicMock, call
from chartmetric_mcp.client import ChartmetricClient
from chartmetric_mcp.auth import AuthError


BASE_URL = "https://api.chartmetric.com/api"


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_token.return_value = "test-token"
    return mgr


@pytest.fixture
def client(mock_token_manager):
    return ChartmetricClient(mock_token_manager)


def test_get_attaches_bearer_token(client, mock_token_manager):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": []}
        client.get("/artist/123")

    mock_get.assert_called_once_with(
        f"{BASE_URL}/artist/123",
        headers={"Authorization": "Bearer test-token"},
        params=None,
        timeout=30,
    )


def test_get_returns_json(client):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"name": "Taylor Swift"}
        result = client.get("/artist/1")

    assert result == {"name": "Taylor Swift"}


def test_404_returns_not_found_message(client):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 404
        result = client.get("/artist/999999")

    assert "not found" in result.lower()


def test_429_returns_rate_limit_message(client):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 429
        result = client.get("/artist/1")

    assert "rate limit" in result.lower()


def test_401_retries_once_then_raises(client, mock_token_manager):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 401
        result = client.get("/artist/1")

    # should have refreshed token and retried once
    assert mock_token_manager.get_token.call_count == 2
    assert "error" in result.lower() or "unauthorized" in result.lower()


def test_network_error_surfaces_message(client):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        result = client.get("/artist/1")

    assert "Connection refused" in result


def test_get_passes_params(client):
    with patch("chartmetric_mcp.client.httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        client.get("/search", params={"q": "taylor", "limit": 100})

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"q": "taylor", "limit": 100}
