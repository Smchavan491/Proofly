"""PayPal OAuth client credentials with an in-memory expiring token cache."""

import os
import time
from dataclasses import dataclass

import httpx

BASE_URL = "https://api-m.sandbox.paypal.com"


@dataclass
class OAuthToken:
    value: str
    expires_at: float


class PayPalAuth:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self.http = http_client or httpx.AsyncClient(base_url=BASE_URL, timeout=20)
        self._owns_client = http_client is None
        self._token: OAuthToken | None = None

    async def get_token(self) -> str:
        if self._token and self._token.expires_at > time.monotonic() + 30:
            return self._token.value
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        secret = os.getenv("PAYPAL_CLIENT_SECRET")
        if not client_id or not secret:
            raise RuntimeError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be configured")
        response = await self.http.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, secret),
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
        )
        response.raise_for_status()
        payload = response.json()
        self._token = OAuthToken(str(payload["access_token"]), time.monotonic() + int(payload["expires_in"]))
        return self._token.value

    async def close(self) -> None:
        if self._owns_client:
            await self.http.aclose()
