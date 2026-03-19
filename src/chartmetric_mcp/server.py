# src/chartmetric_mcp/server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from chartmetric_mcp.auth import TokenManager, AuthError
from chartmetric_mcp.client import ChartmetricClient
from chartmetric_mcp.tools import search as search_tools
from chartmetric_mcp.tools import artist as artist_tools
from chartmetric_mcp.tools import track as track_tools
from chartmetric_mcp.tools import album as album_tools
from chartmetric_mcp.tools import playlist as playlist_tools
from chartmetric_mcp.tools import charts as charts_tools

server = Server("chartmetric-mcp")

# Initialise client once at module level (in-process token cache)
_token_manager: TokenManager | None = None
_client: ChartmetricClient | None = None


def get_client() -> ChartmetricClient:
    global _token_manager, _client
    if _client is None:
        _token_manager = TokenManager()
        _client = ChartmetricClient(_token_manager)
    return _client


TOOLS = [
    types.Tool(name="search", description="Search Chartmetric for artists, tracks, albums, or playlists.", inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "type": {"type": "string", "enum": ["all", "artist", "track", "album", "playlist"], "default": "all"}, "offset": {"type": "integer", "default": 0}}, "required": ["query"]}),
    types.Tool(name="get_artist", description="Get Chartmetric artist metadata.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}}, "required": ["artist_id"]}),
    types.Tool(name="get_artist_fanmetrics", description="Get time-series fan metrics for an artist on a platform.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}, "source": {"type": "string", "enum": ["spotify", "deezer", "facebook", "twitter", "instagram", "youtube_channel", "youtube_artist", "wikipedia", "bandsintown", "soundcloud", "tiktok", "twitch"]}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["artist_id", "source", "start_date"]}),
    types.Tool(name="get_artist_snapshot", description="Get multi-platform snapshot with trend diffs and Chartmetric composite scores.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}}, "required": ["artist_id"]}),
    types.Tool(name="get_artist_charts", description="Get artist chart history.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}, "chart_type": {"type": "string", "enum": ["spotify_viral_daily", "spotify_viral_weekly", "spotify_top_daily", "spotify_top_weekly", "applemusic_top", "applemusic_daily", "applemusic_albums", "itunes_top", "itunes_albums", "shazam", "beatport", "youtube", "youtube_tracks", "youtube_videos", "youtube_trends", "amazon"]}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["artist_id", "chart_type", "start_date"]}),
    types.Tool(name="get_artist_playlists", description="Get playlist placements for an artist.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}, "platform": {"type": "string", "enum": ["spotify", "applemusic", "deezer", "amazon", "youtube"]}, "start_date": {"type": "string"}, "offset": {"type": "integer", "default": 0}}, "required": ["artist_id", "platform", "start_date"]}),
    types.Tool(name="get_artist_cpp", description="Get Chartmetric Performance Points (CPP) history for an artist — the primary historical popularity metric.", inputSchema={"type": "object", "properties": {"artist_id": {"type": "integer"}, "metric": {"type": "string", "enum": ["score", "rank"], "default": "score"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["artist_id"]}),
    types.Tool(name="get_track", description="Get Chartmetric track metadata.", inputSchema={"type": "object", "properties": {"track_id": {"type": "integer"}}, "required": ["track_id"]}),
    types.Tool(name="get_track_stats", description="Get streaming stats over time for a track.", inputSchema={"type": "object", "properties": {"track_id": {"type": "integer"}, "platform": {"type": "string", "enum": ["chartmetric", "spotify", "youtube", "shazam", "tiktok", "genius", "soundcloud", "line", "melon", "radio"]}, "mode": {"type": "string", "enum": ["most-history", "highest-playcounts"], "default": "most-history"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["track_id", "platform"]}),
    types.Tool(name="get_track_charts", description="Get chart history for a track.", inputSchema={"type": "object", "properties": {"track_id": {"type": "integer"}, "chart_type": {"type": "string", "enum": ["spotify_viral_daily", "spotify_viral_weekly", "spotify_top_daily", "spotify_top_weekly", "applemusic_top", "applemusic_daily", "applemusic_albums", "itunes_top", "itunes_albums", "shazam", "beatport", "amazon", "soundcloud", "airplay_daily", "airplay_weekly"]}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["track_id", "chart_type", "start_date"]}),
    types.Tool(name="get_track_playlists", description="Get playlist placements for a track.", inputSchema={"type": "object", "properties": {"track_id": {"type": "integer"}, "platform": {"type": "string", "enum": ["spotify", "applemusic", "deezer", "amazon"]}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "offset": {"type": "integer", "default": 0}}, "required": ["track_id", "platform"]}),
    types.Tool(name="get_album", description="Get Chartmetric album metadata.", inputSchema={"type": "object", "properties": {"album_id": {"type": "integer"}}, "required": ["album_id"]}),
    types.Tool(name="get_album_stats", description="Get Spotify streaming stats for an album.", inputSchema={"type": "object", "properties": {"album_id": {"type": "integer"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["album_id"]}),
    types.Tool(name="get_album_charts", description="Get chart history for an album.", inputSchema={"type": "object", "properties": {"album_id": {"type": "integer"}, "chart_type": {"type": "string", "enum": ["applemusic", "itunes", "amazon"]}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["album_id", "chart_type", "start_date"]}),
    types.Tool(name="get_playlist", description="Get Chartmetric playlist metadata and current tracks.", inputSchema={"type": "object", "properties": {"playlist_id": {"type": "integer"}, "platform": {"type": "string", "enum": ["spotify", "applemusic", "deezer", "amazon", "youtube", "soundcloud"]}}, "required": ["playlist_id", "platform"]}),
    types.Tool(name="browse_playlists", description="Browse top playlists on a platform.", inputSchema={"type": "object", "properties": {"platform": {"type": "string", "enum": ["spotify", "applemusic", "deezer", "amazon", "youtube", "soundcloud"]}, "sort": {"type": "string", "default": "followers"}, "country": {"type": "string", "default": "US"}, "offset": {"type": "integer", "default": 0}}, "required": ["platform"]}),
    types.Tool(name="get_spotify_charts", description="Get Spotify top or viral charts for a date and country.", inputSchema={"type": "object", "properties": {"date": {"type": "string"}, "country": {"type": "string", "default": "US"}, "viral": {"type": "boolean", "default": False}, "offset": {"type": "integer", "default": 0}}, "required": ["date"]}),
    types.Tool(name="get_apple_charts", description="Get Apple Music charts for a date and country.", inputSchema={"type": "object", "properties": {"date": {"type": "string"}, "country": {"type": "string", "default": "US"}, "genre": {"type": "string", "default": "all"}, "offset": {"type": "integer", "default": 0}}, "required": ["date"]}),
    types.Tool(name="get_youtube_charts", description="Get YouTube charts for a date and country. Only available for Thursdays.", inputSchema={"type": "object", "properties": {"date": {"type": "string"}, "country": {"type": "string", "default": "US"}, "offset": {"type": "integer", "default": 0}}, "required": ["date"]}),
    types.Tool(name="get_shazam_charts", description="Get Shazam charts for a date and country, optionally filtered by city.", inputSchema={"type": "object", "properties": {"date": {"type": "string"}, "country": {"type": "string", "default": "US"}, "city": {"type": "string"}, "offset": {"type": "integer", "default": 0}}, "required": ["date"]}),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    client = get_client()
    handlers = {
        "search": lambda a: search_tools.search(client, **a),
        "get_artist": lambda a: artist_tools.get_artist(client, **a),
        "get_artist_fanmetrics": lambda a: artist_tools.get_artist_fanmetrics(client, **a),
        "get_artist_snapshot": lambda a: artist_tools.get_artist_snapshot(client, **a),
        "get_artist_charts": lambda a: artist_tools.get_artist_charts(client, **a),
        "get_artist_playlists": lambda a: artist_tools.get_artist_playlists(client, **a),
        "get_artist_cpp": lambda a: artist_tools.get_artist_cpp(client, **a),
        "get_track": lambda a: track_tools.get_track(client, **a),
        "get_track_stats": lambda a: track_tools.get_track_stats(client, **a),
        "get_track_charts": lambda a: track_tools.get_track_charts(client, **a),
        "get_track_playlists": lambda a: track_tools.get_track_playlists(client, **a),
        "get_album": lambda a: album_tools.get_album(client, **a),
        "get_album_stats": lambda a: album_tools.get_album_stats(client, **a),
        "get_album_charts": lambda a: album_tools.get_album_charts(client, **a),
        "get_playlist": lambda a: playlist_tools.get_playlist(client, **a),
        "browse_playlists": lambda a: playlist_tools.browse_playlists(client, **a),
        "get_spotify_charts": lambda a: charts_tools.get_spotify_charts(client, **a),
        "get_apple_charts": lambda a: charts_tools.get_apple_charts(client, **a),
        "get_youtube_charts": lambda a: charts_tools.get_youtube_charts(client, **a),
        "get_shazam_charts": lambda a: charts_tools.get_shazam_charts(client, **a),
    }
    handler = handlers.get(name)
    if not handler:
        text = f"Unknown tool: {name}"
    else:
        try:
            text = handler(arguments)
        except AuthError as e:
            text = str(e)
        except Exception as e:
            text = f"Error: {e}"
    return [types.TextContent(type="text", text=text)]


def main():
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    asyncio.run(_run())


if __name__ == "__main__":
    main()
