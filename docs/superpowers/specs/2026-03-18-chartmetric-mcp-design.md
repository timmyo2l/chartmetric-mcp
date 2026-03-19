# Chartmetric MCP Server — Design Spec

**Date:** 2026-03-18
**Status:** Approved

---

## Overview

A Python MCP (Model Context Protocol) server that exposes the Chartmetric music analytics API as tools usable by Claude. Enables research into artist popularity history, track stats, chart rankings, playlist placements, and more — directly from a Claude Code session.

---

## Architecture

A single Python package (`chartmetric-mcp`) structured as a stdio MCP server using the official `mcp` Python SDK from Anthropic. Tools are organized by domain. Each tool makes authenticated HTTP calls to the Chartmetric REST API via `httpx`.

```
chartmetric-mcp/
├── src/
│   └── chartmetric_mcp/
│       ├── __init__.py
│       ├── server.py        # MCP server entry point, tool registration
│       ├── auth.py          # Token management (API key → short-lived token)
│       ├── client.py        # Shared httpx client, request helper
│       └── tools/
│           ├── artist.py
│           ├── track.py
│           ├── album.py
│           ├── playlist.py
│           ├── charts.py
│           └── search.py
├── pyproject.toml
└── README.md
```

### Entry Point

`pyproject.toml` defines:
```toml
[project.scripts]
chartmetric-mcp = "chartmetric_mcp.server:main"
```

Registered with Claude Code via:
```bash
claude mcp add -s user chartmetric \
  -e CHARTMETRIC_API_KEY=your_key_here \
  -- uv run --directory /Users/timothyjones/Projects/chartmetric-mcp chartmetric-mcp
```

---

## Authentication

Chartmetric uses a two-credential system:

- **API Key** (`CHARTMETRIC_API_KEY` env var) — the long-lived "Live API Key" emailed by Chartmetric. Also called "refresh token" in Chartmetric's own docs.
- **Short-lived token** — valid for 1 hour. Obtained by `POST https://api.chartmetric.com/api/token` with body `{"refreshtoken": "<api_key>"}`. Returns `{"token": "..."}`. Used as `Authorization: Bearer {token}` on all resource requests.

`auth.py` behaviour:
1. Read `CHARTMETRIC_API_KEY` from environment on startup; fail fast with a clear message if missing
2. Exchange for a short-lived token on first request; cache in-process memory with expiry timestamp
3. In-process caching is intentional — each Claude Code session spawns a fresh process, so the cache starts cold and refreshes once per session automatically
4. Auto-refresh proactively when < 5 minutes remain; proactive refresh failure is non-fatal (the 401-retry path on the subsequent request handles recovery)
5. If the token refresh call itself returns 401 → raise: `"Chartmetric API key is invalid or expired. Check the CHARTMETRIC_API_KEY environment variable."`

---

## Date Format

All date parameters use **`YYYY-MM-DD`** format (ISO 8601 date). Examples: `"2024-01-15"`, `"2023-05-12"`. This applies uniformly across all tools.

---

## MCP Tools

All tools return structured text. **Pagination:** v1 uses a fixed `limit=50` on all list endpoints; no `offset` parameter is exposed to Claude.

---

### Search

#### `search(query, type="all")`
Cross-entity search across artists, tracks, albums, and playlists.
- `query`: search string
- `type`: `"all"` | `"artist"` | `"track"` | `"album"` | `"playlist"`
- Returns: list of matching entities with name, type, and Chartmetric ID

---

### Artist Tools

The distinction between the two main time-series endpoints:
- **`get_artist_fanmetrics`** → granular time-series for a single platform (Chartmetric's `/stat/:source` endpoint). Returns daily data points with value, daily/weekly/monthly diffs.
- **`get_artist_snapshot`** → multi-platform aggregated snapshot with trend summaries (Chartmetric's `/cmStats` endpoint). Returns current values + diffs across all platforms at once.

#### `get_artist(artist_id)`
- Returns: name, genres, country, Spotify/Apple/Deezer/Chartmetric IDs

#### `get_artist_fanmetrics(artist_id, source, start_date, end_date=None)`
- `source`: `spotify` | `deezer` | `facebook` | `twitter` | `instagram` | `youtube_channel` | `youtube_artist` | `wikipedia` | `bandsintown` | `soundcloud` | `tiktok` | `twitch`
- Returns: time-series data points with value and diffs (daily/weekly/monthly)

#### `get_artist_snapshot(artist_id)`
- Returns: current values + weekly/monthly trend diffs across all platforms; includes Chartmetric composite scores (`cm_artist_rank`, `artist_score`, `fan_base_rank`, `engagement_rank`)

#### `get_artist_charts(artist_id, chart_type, start_date, end_date=None)`
- `chart_type`: `spotify_viral_daily` | `spotify_viral_weekly` | `spotify_top_daily` | `spotify_top_weekly` | `applemusic_top` | `applemusic_daily` | `applemusic_albums` | `itunes_top` | `itunes_albums` | `shazam` | `beatport` | `youtube` | `youtube_tracks` | `youtube_videos` | `youtube_trends` | `amazon`
- Returns: chart positions over time

#### `get_artist_playlists(artist_id, platform, start_date)`
- `platform`: `spotify` | `applemusic` | `deezer` | `amazon` | `youtube`
- Returns: playlist placements (up to limit=50)

#### `get_artist_cpp(artist_id, metric="score", start_date=None, end_date=None)`
- Chartmetric Performance Points — Chartmetric's proprietary career performance metric. The primary way to get historical popularity trends for an artist.
- `metric`: `"score"` | `"rank"`
- Returns: time-series of CPP score or rank over the date range

---

### Track Tools

#### `get_track(track_id)`
- Returns: name, artists, ISRC, Spotify/Apple/Chartmetric IDs

#### `get_track_stats(track_id, platform, mode="most-history", start_date=None, end_date=None)`
- `platform`: `chartmetric` | `spotify` | `youtube` | `shazam` | `tiktok` | `genius` | `soundcloud` | `line` | `melon` | `radio`
- `mode`: `"most-history"` | `"highest-playcounts"`
- Returns: streaming stats over time

#### `get_track_charts(track_id, chart_type, start_date, end_date=None)`
- `chart_type`: `spotify_viral_daily` | `spotify_viral_weekly` | `spotify_top_daily` | `spotify_top_weekly` | `applemusic_top` | `applemusic_daily` | `applemusic_albums` | `itunes_top` | `itunes_albums` | `shazam` | `beatport` | `amazon` | `soundcloud` | `airplay_daily` | `airplay_weekly`
- Returns: chart positions over time

#### `get_track_playlists(track_id, platform, start_date=None, end_date=None)`
- `platform`: `spotify` | `applemusic` | `deezer` | `amazon`
- Returns: playlist placements (up to limit=50)

---

### Album Tools

#### `get_album(album_id)`
- Returns: name, artists, release date, track count, Chartmetric/platform IDs

#### `get_album_stats(album_id, platform, start_date=None, end_date=None)`
- `platform`: `spotify` (only platform supported by Chartmetric for album stats)
- Returns: streaming stats over time

#### `get_album_charts(album_id, chart_type, start_date, end_date=None)`
- `chart_type`: `applemusic` | `itunes` | `amazon`
- Returns: chart positions over time

---

### Playlist Tools

#### `get_playlist(playlist_id, platform)`
- `playlist_id`: Chartmetric internal playlist ID (not the platform-native ID)
- `platform`: `spotify` | `applemusic` | `deezer` | `amazon` | `youtube` | `soundcloud`
- Note: Apple Music playlists also require a `storefront` (handled internally, defaulting to `"us"`)
- Returns: playlist metadata + current track list (up to limit=50)

#### `browse_playlists(platform, sort="followers", country="US")`
- `platform`: `spotify` | `applemusic` | `deezer` | `amazon` | `youtube` | `soundcloud`
- `sort`: `followers` | `active_ratio` | `last_updated` | `num_track` | `rank` | `fdiff_week` | `fdiff_month` (availability varies by platform; unsupported values fall back to platform default)
- `country`: ISO 3166-1 alpha-2 country code (e.g. `"US"`, `"GB"`, `"AU"`), passed through to Chartmetric API
- Returns: top playlists matching criteria (up to limit=50)

---

### Charts Tools

All chart tools accept `date` (`YYYY-MM-DD`) and `country` (ISO 3166-1 alpha-2, default `"US"`).

#### `get_spotify_charts(date, country="US", viral=False)`
- `viral=True` returns viral chart; `False` returns top chart
- Returns: ranked track list for the date + country

#### `get_apple_charts(date, country="US", genre="all")`
- Returns: Apple Music top tracks for date + country + genre

#### `get_youtube_charts(date, country="US")`
- Note: YouTube charts update Thursdays only. Pass the date through to the API as-is; if the API returns no data, surface the message: "YouTube charts are only available for Thursdays. Try the nearest Thursday date."
- Returns: YouTube top tracks for date + country

#### `get_shazam_charts(date, country="US", city=None)`
- `city`: optional city name string (e.g. `"San Francisco"`). Must be a valid city for the specified country — use Chartmetric's Shazam Cities endpoint for valid values. When provided, narrows to city-level chart rather than country-level.
- Returns: Shazam top tracks for date + country (+ city if specified)

---

## Data Flow

1. Claude calls an MCP tool (e.g. `get_artist_cpp`)
2. `server.py` routes to the appropriate function in `tools/artist.py`
3. The tool calls `client.py`'s request helper, which:
   - Checks if the cached access token is still valid (> 5 min remaining)
   - If not, calls `auth.py` to refresh it (proactive refresh failure is non-fatal; 401-retry on the request handles it)
   - Makes the `httpx` GET request with `Authorization: Bearer {token}`
4. Response is parsed and returned as structured text to Claude

---

## Error Handling

| Error | Behaviour |
|---|---|
| 401 on resource request | Attempt one token refresh, retry request once, then surface error |
| 401 on token refresh itself | `"Chartmetric API key is invalid or expired. Check the CHARTMETRIC_API_KEY environment variable."` |
| 429 Rate Limited | `"Rate limited by Chartmetric API. Please wait before retrying."` |
| 404 Not Found | `"{Entity type} not found. Verify the ID is correct."` |
| Network / timeout | Surface underlying error message |

---

## Out of Scope

- Write/POST endpoints (Chartmetric API is read-only)
- Response caching
- Multi-user auth
- Pagination beyond fixed limit=50 (v1)
- Configurable API base URL
