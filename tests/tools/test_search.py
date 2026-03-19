# tests/tools/test_search.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.search import search


@pytest.fixture
def client():
    return MagicMock()


def test_search_calls_correct_endpoint(client):
    client.get.return_value = {"data": []}
    search(client, query="Taylor Swift", type="artist")
    client.get.assert_called_once_with(
        "/search/artist",
        params={"q": "Taylor Swift", "limit": 100, "offset": 0},
    )


def test_search_all_uses_multi_endpoint(client):
    client.get.return_value = {"data": []}
    search(client, query="Taylor Swift", type="all")
    client.get.assert_called_once_with(
        "/search/multi",
        params={"q": "Taylor Swift", "limit": 100, "offset": 0},
    )


def test_search_formats_results(client):
    client.get.return_value = {
        "data": [{"id": 1, "name": "Taylor Swift", "type": "artist"}]
    }
    result = search(client, query="Taylor Swift")
    assert "Taylor Swift" in result
    assert "1" in result


def test_search_pagination_prompt(client):
    client.get.return_value = {"data": [{"id": i, "name": f"Artist {i}"} for i in range(100)]}
    result = search(client, query="pop")
    assert "100 results returned" in result
    assert "next page" in result.lower()


def test_search_no_pagination_prompt_under_limit(client):
    client.get.return_value = {"data": [{"id": 1, "name": "Artist"}]}
    result = search(client, query="pop")
    assert "next page" not in result.lower()


def test_search_passes_offset(client):
    client.get.return_value = {"data": []}
    search(client, query="pop", offset=100)
    _, kwargs = client.get.call_args
    assert kwargs["params"]["offset"] == 100


def test_search_returns_error_string(client):
    client.get.return_value = "Error: Rate limited"
    result = search(client, query="pop")
    assert "Rate limited" in result
