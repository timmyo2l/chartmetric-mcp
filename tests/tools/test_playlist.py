# tests/tools/test_playlist.py
import pytest
from unittest.mock import MagicMock
from chartmetric_mcp.tools.playlist import get_playlist, browse_playlists


@pytest.fixture
def client():
    return MagicMock()


def test_get_playlist_endpoint(client):
    client.get.return_value = {"obj": {"name": "Hot Hits", "followers": 500000}}
    result = get_playlist(client, playlist_id=77777, platform="spotify")
    client.get.assert_called_once_with("/playlist/spotify/77777")
    assert "Hot Hits" in result


def test_get_playlist_applemusic_includes_storefront(client):
    client.get.return_value = {"obj": {"name": "New Music Daily"}}
    get_playlist(client, playlist_id=77777, platform="applemusic")
    client.get.assert_called_once_with("/playlist/applemusic/77777", params={"storefront": "us"})


def test_browse_playlists_endpoint(client):
    client.get.return_value = {"data": []}
    browse_playlists(client, platform="spotify", offset=0)
    client.get.assert_called_once_with(
        "/playlist/spotify/lists",
        params={"sortColumn": "followers", "code2": "US", "limit": 100, "offset": 0},
    )


def test_browse_playlists_pagination_prompt(client):
    client.get.return_value = {"data": [{"id": i, "name": f"Playlist {i}"} for i in range(100)]}
    result = browse_playlists(client, platform="spotify")
    assert "next page" in result.lower()
