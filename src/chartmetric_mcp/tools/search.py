# src/chartmetric_mcp/tools/search.py
from chartmetric_mcp.client import ChartmetricClient

PAGINATION_LIMIT = 100
PAGINATION_MSG = "\n\n100 results returned — there may be more. Ask me to load the next page to continue."

TYPE_PARAM = {
    "all": None,
    "artist": "artists",
    "track": "tracks",
    "album": "albums",
    "playlist": "playlists",
}


def search(
    client: ChartmetricClient,
    query: str,
    type: str = "all",
    offset: int = 0,
) -> str:
    params: dict = {"q": query, "limit": PAGINATION_LIMIT, "offset": offset}
    type_param = TYPE_PARAM.get(type)
    if type_param:
        params["type"] = type_param
    result = client.get("/search", params=params)

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
