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
