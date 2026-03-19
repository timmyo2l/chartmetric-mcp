# Chartmetric MCP Server — Design Spec

**Date:** 2026-03-18
**Status:** Approved

---

## Overview

A Python MCP (Model Context Protocol) server that exposes the Chartmetric music analytics API as tools usable by Claude. Enables research into artist popularity history, track stats, chart rankings, playlist placements, and more — directly from a Claude Code session.

---

## Architecture

A single Python package (`chartmetric-mcp`) structured as a stdio MCP server. The entry point launches the server, which registers tools organized by domain. Each tool makes authenticated HTTP calls to the Chartmetric REST API via `httpx`.

```
chartmetric-mcp/
├── src/
│   └── chartmetric_mcp/
│       ├── __init__.py
│       ├── server.py        # MCP server entry point, tool registration
│       ├── auth.py          # Token management (refresh token → access token)
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

---

## Authentication

Chartmetric uses a two-token system:

- **Refresh Token** ("Live API Key") — long-lived, provided by Chartmetric via email. Set as `CHARTMETRIC_REFRESH_TOKEN` env var.
- **Access Token** — short-lived (1 hour), obtained by POSTing the refresh token to `POST https://api.chartmetric.com/api/token`.

`auth.py` handles:
1. Reading `CHARTMETRIC_REFRESH_TOKEN` from the environment
2. Exchanging it for an access token on first request
3. Caching the access token with its expiry timestamp
4. Auto-refreshing when < 5 minutes remain

All API requests include `Authorization: Bearer {access_token}`.

### Configuration

| Env Var | Required | Default | Description |
|---|---|---|---|
| `CHARTMETRIC_REFRESH_TOKEN` | Yes | — | Your Chartmetric Live API Key |
| `CHARTMETRIC_API_URL` | No | `https://api.chartmetric.com/api` | Override for testing |

---

## MCP Tools

### Search
| Tool | Description |
|---|---|
| `search` | Find artists, tracks, albums, playlists by name |

### Artist
| Tool | Description |
|---|---|
| `get_artist` | Metadata (name, genres, country, cross-platform IDs) |
| `get_artist_stats` | Streaming stats over time (Spotify, Apple Music, etc.) |
| `get_artist_charts` | Chart performance history |
| `get_artist_fanmetrics` | Social/fan engagement over time (Instagram, YouTube, Spotify followers) |
| `get_artist_playlists` | Playlist placements |
| `get_artist_cpp` | Chartmetric Performance Points — proprietary popularity score + history |

### Track
| Tool | Description |
|---|---|
| `get_track` | Metadata |
| `get_track_stats` | Streaming stats over time |
| `get_track_charts` | Chart performance history |
| `get_track_playlists` | Playlist placements |

### Album
| Tool | Description |
|---|---|
| `get_album` | Metadata |
| `get_album_stats` | Streaming stats |
| `get_album_charts` | Chart performance |

### Playlist
| Tool | Description |
|---|---|
| `get_playlist` | Metadata + current tracks |
| `browse_playlists` | Discover playlists by platform/followers |

### Charts (platform-specific)
| Tool | Description |
|---|---|
| `get_spotify_charts` | Top/viral tracks by country + date |
| `get_apple_charts` | Apple Music charts |
| `get_youtube_charts` | YouTube charts |
| `get_shazam_charts` | Shazam charts |

---

## Data Flow

1. Claude calls an MCP tool (e.g. `get_artist_cpp`)
2. `server.py` routes to the appropriate function in `tools/artist.py`
3. The tool calls `client.py`'s request helper, which:
   - Checks if the cached access token is still valid (> 5 min remaining)
   - If not, calls `auth.py` to refresh it
   - Makes the `httpx` GET request with `Authorization: Bearer {token}`
4. Response is parsed and returned as structured text to Claude

---

## Error Handling

| Error | Behaviour |
|---|---|
| 401 Unauthorized | Attempt one token refresh, then surface a clear error if it fails |
| 429 Rate Limited | Return error message advising the user to wait before retrying |
| 404 Not Found | Return a user-friendly "not found" message (not a raw HTTP error) |
| Network errors | Surface with the underlying error message |

---

## Installation

Once built, the server is registered in Claude Code via:

```bash
claude mcp add -s user chartmetric \
  -e CHARTMETRIC_REFRESH_TOKEN=your_key_here \
  -- uv run --directory /Users/timothyjones/Projects/chartmetric-mcp chartmetric-mcp
```

---

## Out of Scope

- Write/POST endpoints (Chartmetric API is read-only)
- Caching API responses (not needed for research use)
- Multi-user auth (single-user local tool)
