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
