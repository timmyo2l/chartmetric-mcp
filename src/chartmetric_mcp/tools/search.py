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
