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
