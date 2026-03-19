# tests/tools/test_charts.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.charts import (
    get_spotify_charts, get_apple_charts, get_youtube_charts, get_shazam_charts,
)


@pytest.fixture
def client():
    return MagicMock()


def test_get_spotify_charts_top(client):
    client.get.return_value = {"data": []}
    get_spotify_charts(client, date="2024-01-01", country="US", viral=False)
    client.get.assert_called_once_with(
        "/charts/spotify",
        params={"date": "2024-01-01", "country_code": "US", "viral": 0},
    )


def test_get_spotify_charts_viral(client):
    client.get.return_value = {"data": []}
    get_spotify_charts(client, date="2024-01-01", country="US", viral=True)
    _, kwargs = client.get.call_args
    assert kwargs["params"]["viral"] == 1


def test_get_apple_charts_endpoint(client):
    client.get.return_value = {"data": []}
    get_apple_charts(client, date="2024-01-01", country="US", genre="all")
    client.get.assert_called_once_with(
        "/charts/applemusic",
        params={"date": "2024-01-01", "country_code": "US", "genre": "all"},
    )


def test_get_youtube_charts_endpoint(client):
    client.get.return_value = {"data": [{"name": "Song A"}]}
    get_youtube_charts(client, date="2024-01-04", country="US")
    client.get.assert_called_once_with(
        "/charts/youtube_music",
        params={"date": "2024-01-04", "country_code": "US"},
    )


def test_get_youtube_charts_empty_response_thursday_hint(client):
    client.get.return_value = {"data": []}
    result = get_youtube_charts(client, date="2024-01-01", country="US")
    assert "Thursday" in result


def test_get_shazam_charts_country(client):
    client.get.return_value = {"data": []}
    get_shazam_charts(client, date="2024-01-01", country="US")
    client.get.assert_called_once_with(
        "/charts/shazam",
        params={"date": "2024-01-01", "country_code": "US", "city": None},
    )


def test_get_shazam_charts_with_city(client):
    client.get.return_value = {"data": []}
    get_shazam_charts(client, date="2024-01-01", country="US", city="San Francisco")
    _, kwargs = client.get.call_args
    assert kwargs["params"]["city"] == "San Francisco"


def test_charts_pagination_prompt(client):
    client.get.return_value = {"data": [{"name": f"Song {i}"} for i in range(100)]}
    result = get_spotify_charts(client, date="2024-01-01")
    assert "next page" in result.lower()
