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
