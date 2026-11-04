"""PayPal disputes API operations."""

from typing import Any

import httpx

from app.paypal.auth import PayPalAuth


class Disputes:
    def __init__(self, auth: PayPalAuth, http_client: httpx.AsyncClient) -> None:
        self.auth, self.http = auth, http_client

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        token = await self.auth.get_token()
        response = await self.http.request(method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    async def list_disputes(self, **params: Any) -> dict[str, Any]:
        return await self._request("GET", "/v1/customer/disputes", params=params)

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/customer/disputes/{dispute_id}")

    async def provide_evidence(self, dispute_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/customer/disputes/{dispute_id}/provide-evidence", json=evidence)

    async def make_offer(self, dispute_id: str, offer: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/customer/disputes/{dispute_id}/make-offer", json=offer)

    async def accept_claim(self, dispute_id: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", f"/v1/customer/disputes/{dispute_id}/accept-claim", json=request or {})

    async def send_message(self, dispute_id: str, message: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/customer/disputes/{dispute_id}/send-message", json=message)
