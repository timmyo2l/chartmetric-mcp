# Chartmetric MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server that exposes the Chartmetric music analytics API as Claude tools for music research.

**Architecture:** Stdio MCP server using the official `mcp` Python SDK. Auth module exchanges the long-lived API key for a short-lived bearer token (cached in-process, auto-refreshed). A shared `httpx` client handles all requests with unified error handling. Tools are organized into domain modules (artist, track, album, playlist, charts, search) and registered in `server.py`.

**Tech Stack:** Python 3.11+, `mcp` (Anthropic MCP SDK), `httpx` (HTTP client), `pytest` + `pytest-mock` (testing), `uv` (package manager)

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, entry point |
| `src/chartmetric_mcp/__init__.py` | Package marker |
| `src/chartmetric_mcp/auth.py` | API key → bearer token exchange, in-process caching, auto-refresh |
| `src/chartmetric_mcp/client.py` | Shared httpx client, `get()` helper with error handling + 401-retry |
| `src/chartmetric_mcp/tools/__init__.py` | Package marker |
| `src/chartmetric_mcp/tools/search.py` | `search` tool |
| `src/chartmetric_mcp/tools/artist.py` | 6 artist tools |
| `src/chartmetric_mcp/tools/track.py` | 4 track tools |
| `src/chartmetric_mcp/tools/album.py` | 3 album tools |
| `src/chartmetric_mcp/tools/playlist.py` | 2 playlist tools |
| `src/chartmetric_mcp/tools/charts.py` | 4 chart tools |
| `src/chartmetric_mcp/server.py` | MCP server entry point, tool registration |
| `tests/__init__.py` | Package marker |
| `tests/test_auth.py` | Auth module tests |
| `tests/test_client.py` | HTTP client tests |
| `tests/tools/test_search.py` | Search tool tests |
| `tests/tools/test_artist.py` | Artist tool tests |
| `tests/tools/test_track.py` | Track tool tests |
| `tests/tools/test_album.py` | Album tool tests |
| `tests/tools/test_playlist.py` | Playlist tool tests |
| `tests/tools/test_charts.py` | Charts tool tests |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/chartmetric_mcp/__init__.py`
- Create: `src/chartmetric_mcp/tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/tools/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "chartmetric-mcp"
version = "0.1.0"
description = "MCP server for the Chartmetric music analytics API"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
]

[project.scripts]
chartmetric-mcp = "chartmetric_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["src/chartmetric_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]
```

- [ ] **Step 2: Create directory structure and empty init files**

```bash
mkdir -p src/chartmetric_mcp/tools tests/tools
touch src/chartmetric_mcp/__init__.py
touch src/chartmetric_mcp/tools/__init__.py
touch tests/__init__.py
touch tests/tools/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
uv sync --dev
```

Expected: dependencies installed with no errors.

- [ ] **Step 4: Verify pytest runs**

```bash
uv run pytest
```

Expected: `no tests ran` (0 collected).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: scaffold project structure"
```

---

## Task 2: Auth Module

**Files:**
- Create: `src/chartmetric_mcp/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth.py
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from chartmetric_mcp.auth import TokenManager, AuthError


def test_raises_if_api_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(AuthError, match="CHARTMETRIC_API_KEY"):
            TokenManager()


def test_fetches_token_on_first_call(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "test-token-123"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        token = mgr.get_token()

    assert token == "test-token-123"
    mock_httpx_post.assert_called_once_with(
        "https://api.chartmetric.com/api/token",
        json={"refreshtoken": "my-api-key"},
        timeout=10,
    )


def test_caches_token_within_expiry(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "cached-token"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        token1 = mgr.get_token()
        token2 = mgr.get_token()

    assert token1 == token2
    assert mock_httpx_post.call_count == 1  # only fetched once


def test_refreshes_when_near_expiry(mock_httpx_post):
    mock_httpx_post.return_value.json.return_value = {"token": "new-token"}
    mock_httpx_post.return_value.status_code = 200

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "my-api-key"}):
        mgr = TokenManager()
        mgr._token = "old-token"
        mgr._expires_at = time.time() + 200  # < 5 min remaining
        token = mgr.get_token()

    assert token == "new-token"


def test_raises_on_401_from_token_endpoint(mock_httpx_post):
    mock_httpx_post.return_value.status_code = 401

    with patch.dict(os.environ, {"CHARTMETRIC_API_KEY": "bad-key"}):
        mgr = TokenManager()
        with pytest.raises(AuthError, match="invalid or expired"):
            mgr.get_token()


@pytest.fixture
def mock_httpx_post():
    with patch("chartmetric_mcp.auth.httpx.post") as mock:
        yield mock
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'chartmetric_mcp.auth'`

- [ ] **Step 3: Implement `auth.py`**

```python
# src/chartmetric_mcp/auth.py
import os
import time
import httpx


class AuthError(Exception):
    pass


class TokenManager:
    _TOKEN_URL = "https://api.chartmetric.com/api/token"
    _REFRESH_THRESHOLD = 300  # refresh if < 5 minutes remain
    _TOKEN_TTL = 3600  # Chartmetric tokens last 1 hour

    def __init__(self):
        self._api_key = os.environ.get("CHARTMETRIC_API_KEY")
        if not self._api_key:
            raise AuthError(
                "CHARTMETRIC_API_KEY environment variable is not set. "
                "Set it to your Chartmetric Live API Key."
            )
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if self._token and time.time() < self._expires_at - self._REFRESH_THRESHOLD:
            return self._token
        return self._refresh()

    def _refresh(self) -> str:
        response = httpx.post(
            self._TOKEN_URL,
            json={"refreshtoken": self._api_key},
            timeout=10,
        )
        if response.status_code == 401:
            raise AuthError(
                "Chartmetric API key is invalid or expired. "
                "Check the CHARTMETRIC_API_KEY environment variable."
            )
        response.raise_for_status()
        self._token = response.json()["token"]
        self._expires_at = time.time() + self._TOKEN_TTL
        return self._token
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/auth.py tests/test_auth.py
git commit -m "feat: add auth module with token caching and refresh"
```

---

## Task 3: HTTP Client

**Files:**
- Create: `src/chartmetric_mcp/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'chartmetric_mcp.client'`

- [ ] **Step 3: Implement `client.py`**

```python
# src/chartmetric_mcp/client.py
import httpx
from chartmetric_mcp.auth import TokenManager

BASE_URL = "https://api.chartmetric.com/api"


class ChartmetricClient:
    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager
        self._retried = False

    def get(self, path: str, params: dict | None = None) -> dict | str:
        try:
            token = self._token_manager.get_token()
            response = httpx.get(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=30,
            )
        except Exception as e:
            return f"Network error: {e}"

        if response.status_code == 200:
            self._retried = False
            return response.json()

        if response.status_code == 401 and not self._retried:
            self._retried = True
            # Force token refresh by invalidating cache
            self._token_manager._token = None
            self._token_manager._expires_at = 0.0
            return self.get(path, params)

        self._retried = False

        if response.status_code == 401:
            return "Error: Unauthorized after token refresh. Check your Chartmetric API key."

        if response.status_code == 404:
            return "Error: Resource not found. Verify the ID is correct."

        if response.status_code == 429:
            return "Error: Rate limited by Chartmetric API. Please wait before retrying."

        return f"Error: Chartmetric API returned status {response.status_code}."
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_client.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/client.py tests/test_client.py
git commit -m "feat: add http client with error handling and 401 retry"
```

---

## Task 4: Search Tool

**Files:**
- Create: `src/chartmetric_mcp/tools/search.py`
- Create: `tests/tools/test_search.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_search.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/search.py`**

```python
# src/chartmetric_mcp/tools/search.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."

TYPE_TO_ENDPOINT = {
    "all": "/search/multi",
    "artist": "/search/artist",
    "track": "/search/track",
    "album": "/search/album",
    "playlist": "/search/playlist",
}


def search(
    client: ChartmetricClient,
    query: str,
    type: str = "all",
    offset: int = 0,
) -> str:
    endpoint = TYPE_TO_ENDPOINT.get(type, "/search/multi")
    result = client.get(endpoint, params={"q": query, "limit": PAGINATION_LIMIT, "offset": offset})

    if isinstance(result, str):
        return result

    items = result.get("data", [])
    if not items:
        return "No results found."

    lines = [f"- [{item.get('type', type)}] {item.get('name', 'Unknown')} (ID: {item.get('id', '?')})" for item in items]
    output = "\n".join(lines)

    if len(items) >= PAGINATION_LIMIT:
        output += PAGINATION_MSG

    return output
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_search.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/search.py tests/tools/test_search.py
git commit -m "feat: add search tool"
```

---

## Task 5: Artist Tools

**Files:**
- Create: `src/chartmetric_mcp/tools/artist.py`
- Create: `tests/tools/test_artist.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_artist.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/artist.py`**

```python
# src/chartmetric_mcp/tools/artist.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."


def get_artist(client: ChartmetricClient, artist_id: int) -> str:
    result = client.get(f"/artist/{artist_id}")
    if isinstance(result, str):
        return result
    obj = result.get("obj", {})
    lines = [
        f"Name: {obj.get('name', 'Unknown')}",
        f"Genres: {', '.join(obj.get('genres', [])) or 'N/A'}",
        f"Country: {obj.get('countryCode', 'N/A')}",
        f"Chartmetric ID: {artist_id}",
        f"Spotify ID: {obj.get('spotify_artist_ids', ['N/A'])[0] if obj.get('spotify_artist_ids') else 'N/A'}",
    ]
    return "\n".join(lines)


def get_artist_fanmetrics(
    client: ChartmetricClient,
    artist_id: int,
    source: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/artist/{artist_id}/stat/{source}",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No fan metrics found for artist {artist_id} on {source}."
    lines = [f"{d.get('timestp', '?')}: {d.get('value', '?')}" for d in data]
    return f"Fan metrics ({source}) for artist {artist_id}:\n" + "\n".join(lines)


def get_artist_snapshot(client: ChartmetricClient, artist_id: int) -> str:
    result = client.get(f"/artist/{artist_id}/cmStats")
    if isinstance(result, str):
        return result
    import json
    return json.dumps(result.get("obj", result), indent=2)


def get_artist_charts(
    client: ChartmetricClient,
    artist_id: int,
    chart_type: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/artist/{artist_id}/{chart_type}/charts",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No chart data found for artist {artist_id} on {chart_type}."
    lines = [f"{d.get('timestp', d.get('date', '?'))}: rank {d.get('rank', '?')}" for d in data]
    return f"{chart_type} chart history for artist {artist_id}:\n" + "\n".join(lines)


def get_artist_playlists(
    client: ChartmetricClient,
    artist_id: int,
    platform: str,
    start_date: str,
    offset: int = 0,
) -> str:
    result = client.get(
        f"/artist/{artist_id}/{platform}/current/playlists",
        params={"since": start_date, "limit": PAGINATION_LIMIT, "offset": offset},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No playlist placements found for artist {artist_id} on {platform}."
    lines = [f"- {p.get('name', 'Unknown')} (ID: {p.get('id', '?')})" for p in data]
    output = f"Playlist placements ({platform}) for artist {artist_id}:\n" + "\n".join(lines)
    if len(data) >= PAGINATION_LIMIT:
        output += PAGINATION_MSG
    return output


def get_artist_cpp(
    client: ChartmetricClient,
    artist_id: int,
    metric: str = "score",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/artist/{artist_id}/cpp",
        params={"stat": metric, "since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No CPP data found for artist {artist_id}."
    lines = [f"{d.get('timestp', '?')}: {metric} = {d.get(metric, d.get('value', '?'))}" for d in data]
    return f"Chartmetric Performance Points ({metric}) for artist {artist_id}:\n" + "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_artist.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/artist.py tests/tools/test_artist.py
git commit -m "feat: add artist tools"
```

---

## Task 6: Track Tools

**Files:**
- Create: `src/chartmetric_mcp/tools/track.py`
- Create: `tests/tools/test_track.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to confirm fail**

```bash
uv run pytest tests/tools/test_track.py -v
```

- [ ] **Step 3: Implement `tools/track.py`**

```python
# src/chartmetric_mcp/tools/track.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."


def get_track(client: ChartmetricClient, track_id: int) -> str:
    result = client.get(f"/track/{track_id}")
    if isinstance(result, str):
        return result
    obj = result.get("obj", {})
    lines = [
        f"Name: {obj.get('name', 'Unknown')}",
        f"ISRC: {obj.get('isrc', 'N/A')}",
        f"Artists: {', '.join(a.get('name', '') for a in obj.get('artists', [])) or 'N/A'}",
        f"Chartmetric ID: {track_id}",
    ]
    return "\n".join(lines)


def get_track_stats(
    client: ChartmetricClient,
    track_id: int,
    platform: str,
    mode: str = "most-history",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/track/{track_id}/{platform}/stats/{mode}",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No stats found for track {track_id} on {platform}."
    lines = [f"{d.get('timestp', '?')}: {d}" for d in data[:20]]
    return f"Stats ({platform}, {mode}) for track {track_id}:\n" + "\n".join(lines)


def get_track_charts(
    client: ChartmetricClient,
    track_id: int,
    chart_type: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/track/{track_id}/{chart_type}/charts",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No chart data found for track {track_id} on {chart_type}."
    lines = [f"{d.get('timestp', d.get('date', '?'))}: rank {d.get('rank', '?')}" for d in data]
    return f"{chart_type} chart history for track {track_id}:\n" + "\n".join(lines)


def get_track_playlists(
    client: ChartmetricClient,
    track_id: int,
    platform: str,
    start_date: str | None = None,
    end_date: str | None = None,
    offset: int = 0,
) -> str:
    result = client.get(
        f"/track/{track_id}/{platform}/current/playlists",
        params={"since": start_date, "until": end_date, "limit": PAGINATION_LIMIT, "offset": offset},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No playlist placements found for track {track_id} on {platform}."
    lines = [f"- {p.get('name', 'Unknown')} (ID: {p.get('id', '?')})" for p in data]
    output = f"Playlist placements ({platform}) for track {track_id}:\n" + "\n".join(lines)
    if len(data) >= PAGINATION_LIMIT:
        output += PAGINATION_MSG
    return output
```

- [ ] **Step 4: Run to confirm pass**

```bash
uv run pytest tests/tools/test_track.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/track.py tests/tools/test_track.py
git commit -m "feat: add track tools"
```

---

## Task 7: Album Tools

**Files:**
- Create: `src/chartmetric_mcp/tools/album.py`
- Create: `tests/tools/test_album.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to confirm fail**

```bash
uv run pytest tests/tools/test_album.py -v
```

- [ ] **Step 3: Implement `tools/album.py`**

```python
# src/chartmetric_mcp/tools/album.py
from chartmetric_mcp.client import ChartmetricClient


def get_album(client: ChartmetricClient, album_id: int) -> str:
    result = client.get(f"/album/{album_id}")
    if isinstance(result, str):
        return result
    obj = result.get("obj", {})
    lines = [
        f"Name: {obj.get('name', 'Unknown')}",
        f"Release date: {obj.get('release_date', 'N/A')}",
        f"Track count: {obj.get('num_tracks', 'N/A')}",
        f"Artists: {', '.join(a.get('name', '') for a in obj.get('artists', [])) or 'N/A'}",
        f"Chartmetric ID: {album_id}",
    ]
    return "\n".join(lines)


def get_album_stats(
    client: ChartmetricClient,
    album_id: int,
    platform: str = "spotify",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/album/{album_id}/{platform}/stats",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No stats found for album {album_id} on {platform}."
    lines = [f"{d.get('timestp', '?')}: {d}" for d in data]
    return f"Stats ({platform}) for album {album_id}:\n" + "\n".join(lines)


def get_album_charts(
    client: ChartmetricClient,
    album_id: int,
    chart_type: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    result = client.get(
        f"/album/{album_id}/{chart_type}/charts",
        params={"since": start_date, "until": end_date},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No chart data found for album {album_id} on {chart_type}."
    lines = [f"{d.get('timestp', d.get('date', '?'))}: rank {d.get('rank', '?')}" for d in data]
    return f"{chart_type} chart history for album {album_id}:\n" + "\n".join(lines)
```

- [ ] **Step 4: Run to confirm pass**

```bash
uv run pytest tests/tools/test_album.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/album.py tests/tools/test_album.py
git commit -m "feat: add album tools"
```

---

## Task 8: Playlist Tools

**Files:**
- Create: `src/chartmetric_mcp/tools/playlist.py`
- Create: `tests/tools/test_playlist.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to confirm fail**

```bash
uv run pytest tests/tools/test_playlist.py -v
```

- [ ] **Step 3: Implement `tools/playlist.py`**

```python
# src/chartmetric_mcp/tools/playlist.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."


def get_playlist(client: ChartmetricClient, playlist_id: int, platform: str) -> str:
    params = {"storefront": "us"} if platform == "applemusic" else None
    kwargs = {"params": params} if params else {}
    result = client.get(f"/playlist/{platform}/{playlist_id}", **kwargs)
    if isinstance(result, str):
        return result
    obj = result.get("obj", {})
    lines = [
        f"Name: {obj.get('name', 'Unknown')}",
        f"Followers: {obj.get('followers', 'N/A'):,}" if isinstance(obj.get('followers'), int) else f"Followers: {obj.get('followers', 'N/A')}",
        f"Platform: {platform}",
        f"Chartmetric ID: {playlist_id}",
    ]
    return "\n".join(lines)


def browse_playlists(
    client: ChartmetricClient,
    platform: str,
    sort: str = "followers",
    country: str = "US",
    offset: int = 0,
) -> str:
    result = client.get(
        f"/playlist/{platform}/lists",
        params={"sortColumn": sort, "code2": country, "limit": PAGINATION_LIMIT, "offset": offset},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No playlists found on {platform}."
    lines = [f"- {p.get('name', 'Unknown')} (ID: {p.get('id', '?')}, followers: {p.get('followers', 'N/A')})" for p in data]
    output = f"Top playlists on {platform} (sorted by {sort}, {country}):\n" + "\n".join(lines)
    if len(data) >= PAGINATION_LIMIT:
        output += PAGINATION_MSG
    return output
```

- [ ] **Step 4: Run to confirm pass**

```bash
uv run pytest tests/tools/test_playlist.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/playlist.py tests/tools/test_playlist.py
git commit -m "feat: add playlist tools"
```

---

## Task 9: Charts Tools

**Files:**
- Create: `src/chartmetric_mcp/tools/charts.py`
- Create: `tests/tools/test_charts.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to confirm fail**

```bash
uv run pytest tests/tools/test_charts.py -v
```

- [ ] **Step 3: Implement `tools/charts.py`**

```python
# src/chartmetric_mcp/tools/charts.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."


def _format_chart_results(data: list, label: str) -> str:
    lines = [f"{i+1}. {t.get('name', 'Unknown')} — {t.get('artist_name', t.get('artists', '?'))}" for i, t in enumerate(data)]
    output = f"{label}:\n" + "\n".join(lines)
    if len(data) >= PAGINATION_LIMIT:
        output += PAGINATION_MSG
    return output


def get_spotify_charts(
    client: ChartmetricClient,
    date: str,
    country: str = "US",
    viral: bool = False,
    offset: int = 0,
) -> str:
    result = client.get(
        "/charts/spotify",
        params={"date": date, "country_code": country, "viral": 1 if viral else 0},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No Spotify charts found for {date} in {country}."
    chart_type = "Viral" if viral else "Top"
    return _format_chart_results(data, f"Spotify {chart_type} chart ({country}, {date})")


def get_apple_charts(
    client: ChartmetricClient,
    date: str,
    country: str = "US",
    genre: str = "all",
    offset: int = 0,
) -> str:
    result = client.get(
        "/charts/applemusic",
        params={"date": date, "country_code": country, "genre": genre},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return f"No Apple Music charts found for {date} in {country}."
    return _format_chart_results(data, f"Apple Music chart ({country}, {date}, genre: {genre})")


def get_youtube_charts(
    client: ChartmetricClient,
    date: str,
    country: str = "US",
    offset: int = 0,
) -> str:
    result = client.get(
        "/charts/youtube_music",
        params={"date": date, "country_code": country},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    if not data:
        return (
            f"No YouTube charts found for {date} in {country}. "
            "YouTube charts are only available for Thursdays. Try the nearest Thursday date."
        )
    return _format_chart_results(data, f"YouTube chart ({country}, {date})")


def get_shazam_charts(
    client: ChartmetricClient,
    date: str,
    country: str = "US",
    city: str | None = None,
    offset: int = 0,
) -> str:
    result = client.get(
        "/charts/shazam",
        params={"date": date, "country_code": country, "city": city},
    )
    if isinstance(result, str):
        return result
    data = result.get("data", [])
    location = f"{city}, {country}" if city else country
    if not data:
        return f"No Shazam charts found for {date} in {location}."
    return _format_chart_results(data, f"Shazam chart ({location}, {date})")
```

- [ ] **Step 4: Run to confirm pass**

```bash
uv run pytest tests/tools/test_charts.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/tools/charts.py tests/tools/test_charts.py
git commit -m "feat: add charts tools"
```

---

## Task 10: Server Entry Point

**Files:**
- Create: `src/chartmetric_mcp/server.py`

- [ ] **Step 1: Run all tests to confirm baseline**

```bash
uv run pytest -v
```

Expected: all existing tests PASS before adding server.

- [ ] **Step 2: Implement `server.py`**

```python
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
```

- [ ] **Step 3: Run all tests to confirm nothing broken**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Smoke test the server starts**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' | CHARTMETRIC_API_KEY=test uv run chartmetric-mcp 2>/dev/null | head -1
```

Expected: a JSON response beginning with `{"jsonrpc":"2.0"`.

- [ ] **Step 5: Commit**

```bash
git add src/chartmetric_mcp/server.py
git commit -m "feat: add server entry point with all 20 tools registered"
```

---

## Task 11: Register with Claude Code

- [ ] **Step 1: Register the MCP server**

```bash
claude mcp add -s user chartmetric \
  -e CHARTMETRIC_API_KEY=your_live_api_key_here \
  -- uv run --directory /Users/timothyjones/Projects/chartmetric-mcp chartmetric-mcp
```

Replace `your_live_api_key_here` with the actual Chartmetric Live API Key.

- [ ] **Step 2: Restart Claude Code session and verify**

Open `/mcp` in Claude Code. The `chartmetric` server should appear with a green checkmark.

- [ ] **Step 3: Smoke test a real tool call**

Ask Claude: "Search Chartmetric for Maryon King"

Expected: list of matching results with Chartmetric IDs.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: project complete — chartmetric mcp server ready"
```
