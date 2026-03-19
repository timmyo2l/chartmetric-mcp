# tests/tools/test_track.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.track import (
    get_track, get_track_stats, get_track_charts, get_track_playlists,
)


@pytest.fixture
def client():
    return MagicMock()


def test_get_track_endpoint(client):
    client.get.return_value = {"obj": {"name": "Shake It Off", "isrc": "USCJY1431878"}}
    result = get_track(client, track_id=99999)
    client.get.assert_called_once_with("/track/99999")
    assert "Shake It Off" in result


def test_get_track_stats_endpoint(client):
    client.get.return_value = {"data": []}
    get_track_stats(client, track_id=99999, platform="spotify", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/track/99999/spotify/stats/most-history",
        params={"since": "2024-01-01", "until": None},
    )


def test_get_track_stats_highest_playcounts_mode(client):
    client.get.return_value = {"data": []}
    get_track_stats(client, track_id=99999, platform="spotify", mode="highest-playcounts")
    client.get.assert_called_once_with(
        "/track/99999/spotify/stats/highest-playcounts",
        params={"since": None, "until": None},
    )


def test_get_track_charts_endpoint(client):
    client.get.return_value = {"data": []}
    get_track_charts(client, track_id=99999, chart_type="spotify_top_daily", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/track/99999/spotify_top_daily/charts",
        params={"since": "2024-01-01", "until": None},
    )


def test_get_track_playlists_endpoint(client):
    client.get.return_value = {"data": [], "total": 0}
    get_track_playlists(client, track_id=99999, platform="spotify", offset=0)
    client.get.assert_called_once_with(
        "/track/99999/spotify/current/playlists",
        params={"since": None, "until": None, "limit": 100, "offset": 0},
    )


def test_track_playlists_pagination_prompt(client):
    client.get.return_value = {"data": [{"id": i} for i in range(100)]}
    result = get_track_playlists(client, track_id=1, platform="spotify")
    assert "next page" in result.lower()
