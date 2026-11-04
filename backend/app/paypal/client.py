"""Unified async interface for mock and PayPal sandbox clients."""

import os
from typing import Any

import httpx

from app.paypal.auth import BASE_URL, PayPalAuth
from app.paypal.disputes import Disputes
from app.paypal.orders import Orders


class PayPalClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self.http = http_client or httpx.AsyncClient(base_url=BASE_URL, timeout=20)
        self.auth = PayPalAuth(self.http)
        self.orders = Orders(self.auth, self.http)
        self.disputes = Disputes(self.auth, self.http)

    async def create_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return await self.orders.create_order(order)

    async def capture_order(self, order_id: str) -> dict[str, Any]:
        return await self.orders.capture_order(order_id)

    async def list_disputes(self, **params: Any) -> dict[str, Any]:
        return await self.disputes.list_disputes(**params)

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return await self.disputes.get_dispute(dispute_id)

    async def provide_evidence(self, dispute_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return await self.disputes.provide_evidence(dispute_id, evidence)

    async def make_offer(self, dispute_id: str, offer: dict[str, Any]) -> dict[str, Any]:
        return await self.disputes.make_offer(dispute_id, offer)

    async def accept_claim(self, dispute_id: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.disputes.accept_claim(dispute_id, request)

    async def send_message(self, dispute_id: str, message: dict[str, Any]) -> dict[str, Any]:
        return await self.disputes.send_message(dispute_id, message)

    async def close(self) -> None:
        await self.http.aclose()


class MockPayPalClient:
    """In-memory API-compatible fake; write methods intentionally have no external effect."""

    def __init__(self) -> None:
        self.orders_by_id: dict[str, dict[str, Any]] = {}
        self.disputes_by_id: dict[str, dict[str, Any]] = {}

    async def create_order(self, order: dict[str, Any]) -> dict[str, Any]:
        order_id = f"MOCK-{len(self.orders_by_id) + 1}"
        result = {"id": order_id, "status": "CREATED", **order}
        self.orders_by_id[order_id] = result
        return result

    async def capture_order(self, order_id: str) -> dict[str, Any]:
        result = {**self.orders_by_id[order_id], "status": "COMPLETED"}
        self.orders_by_id[order_id] = result
        return result

    async def list_disputes(self, **params: Any) -> dict[str, Any]:
        return {"items": list(self.disputes_by_id.values()), "count": len(self.disputes_by_id)}

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return self.disputes_by_id[dispute_id]

    async def provide_evidence(self, dispute_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return {"dispute_id": dispute_id, "status": "SUBMITTED", "evidence": evidence}

    async def make_offer(self, dispute_id: str, offer: dict[str, Any]) -> dict[str, Any]:
        return {"dispute_id": dispute_id, "status": "OFFERED", "offer": offer}

    async def accept_claim(self, dispute_id: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"dispute_id": dispute_id, "status": "ACCEPTED"}

    async def send_message(self, dispute_id: str, message: dict[str, Any]) -> dict[str, Any]:
        return {"dispute_id": dispute_id, "status": "SENT", "message": message}

    async def close(self) -> None:
        return None


def get_paypal_client(http_client: httpx.AsyncClient | None = None) -> PayPalClient | MockPayPalClient:
    return MockPayPalClient() if os.getenv("MOCK_PAYPAL", "true").lower() in {"1", "true", "yes", "on"} else PayPalClient(http_client)
