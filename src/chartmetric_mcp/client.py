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
