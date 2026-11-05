"""PayPal Orders v2 operations."""

import copy
import os
from typing import Any

import httpx

from app.paypal.auth import PayPalAuth


class Orders:
    def __init__(self, auth: PayPalAuth, http_client: httpx.AsyncClient) -> None:
        self.auth, self.http = auth, http_client

    async def create_order(self, order: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(order)
        currency = os.getenv("PAYPAL_CURRENCY", "USD").strip().upper() or "USD"
        for unit in payload.get("purchase_units", []):
            amount = unit.setdefault("amount", {})
            amount["currency_code"] = currency
        token = await self.auth.get_token()
        response = await self.http.post(
            "/v2/checkout/orders",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Prefer": "return=representation"},
        )
        response.raise_for_status()
        return response.json()

    async def capture_order(self, order_id: str) -> dict[str, Any]:
        token = await self.auth.get_token()
        response = await self.http.post(f"/v2/checkout/orders/{order_id}/capture", json={}, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()

    async def get_order(self, order_id: str) -> dict[str, Any]:
        token = await self.auth.get_token()
        response = await self.http.get(f"/v2/checkout/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()
