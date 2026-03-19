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
