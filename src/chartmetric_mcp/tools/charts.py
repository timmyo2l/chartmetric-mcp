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
