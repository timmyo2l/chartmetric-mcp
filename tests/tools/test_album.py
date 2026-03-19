# tests/tools/test_album.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.album import get_album, get_album_stats, get_album_charts


@pytest.fixture
def client():
    return MagicMock()


def test_get_album_endpoint(client):
    client.get.return_value = {"obj": {"name": "1989", "release_date": "2014-10-27"}}
    result = get_album(client, album_id=55555)
    client.get.assert_called_once_with("/album/55555")
    assert "1989" in result


def test_get_album_stats_endpoint(client):
    client.get.return_value = {"data": []}
    get_album_stats(client, album_id=55555, platform="spotify", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/album/55555/spotify/stats",
        params={"since": "2024-01-01", "until": None},
    )


def test_get_album_charts_endpoint(client):
    client.get.return_value = {"data": []}
    get_album_charts(client, album_id=55555, chart_type="applemusic", start_date="2024-01-01")
    client.get.assert_called_once_with(
        "/album/55555/applemusic/charts",
        params={"since": "2024-01-01", "until": None},
    )
