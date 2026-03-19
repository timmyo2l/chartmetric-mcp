# tests/tools/test_artist.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.artist import (
    get_artist, get_artist_fanmetrics, get_artist_snapshot,
    get_artist_charts, get_artist_playlists, get_artist_cpp,
)


@pytest.fixture
def client():
    return MagicMock()


def test_get_artist_calls_correct_endpoint(client):
    client.get.return_value = {"obj": {"name": "Taylor Swift", "genres": ["pop"]}}
    result = get_artist(client, artist_id=12345)
    client.get.assert_called_once_with("/artist/12345")
    assert "Taylor Swift" in result


def test_get_artist_fanmetrics_endpoint(client):
    client.get.return_value = {"data": [{"timestp": "2024-01-01", "value": 1000}]}
    get_artist_fanmetrics(client, artist_id=12345, source="spotify", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/artist/12345/stat/spotify",
        params={"since": "2024-01-01", "until": None},
    )


def test_get_artist_snapshot_endpoint(client):
    client.get.return_value = {"obj": {"spotify": {"followers": 5000000}}}
    get_artist_snapshot(client, artist_id=12345)
    client.get.assert_called_once_with("/artist/12345/cmStats")


def test_get_artist_charts_endpoint(client):
    client.get.return_value = {"data": []}
    get_artist_charts(client, artist_id=12345, chart_type="spotify_top_daily", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/artist/12345/spotify_top_daily/charts",
        params={"since": "2024-01-01", "until": None},
    )


def test_get_artist_playlists_endpoint(client):
    client.get.return_value = {"data": [], "total": 0}
    get_artist_playlists(client, artist_id=12345, platform="spotify", start_date="2024-01-01", offset=0)
    client.get.assert_called_once_with(
        "/artist/12345/spotify/current/playlists",
        params={"since": "2024-01-01", "limit": 100, "offset": 0},
    )


def test_get_artist_cpp_endpoint(client):
    client.get.return_value = {"data": [{"timestp": "2024-01-01", "score": 85}]}
    get_artist_cpp(client, artist_id=12345, metric="score", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/artist/12345/cpp",
        params={"stat": "score", "since": "2024-01-01", "until": None},
    )


def test_artist_playlists_pagination_prompt(client):
    client.get.return_value = {"data": [{"id": i} for i in range(100)]}
    result = get_artist_playlists(client, artist_id=1, platform="spotify", start_date="2024-01-01")
    assert "next page" in result.lower()


def test_get_artist_returns_error_passthrough(client):
    client.get.return_value = "Error: Not found."
    result = get_artist(client, artist_id=9999)
    assert "Error" in result
