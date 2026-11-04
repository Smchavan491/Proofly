"""PayPal webhook verification, event routing, and dispute polling fallback."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.paypal.auth import BASE_URL
from app.paypal.client import get_paypal_client

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]
router = APIRouter()


async def verify_webhook_signature(headers: dict[str, str], event: dict[str, Any], http: httpx.AsyncClient | None = None) -> bool:
    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID")
    if not webhook_id:
        return False
    owns_client = http is None
    client = http or httpx.AsyncClient(base_url=BASE_URL, timeout=20)
    try:
        client_id, secret = os.getenv("PAYPAL_CLIENT_ID"), os.getenv("PAYPAL_CLIENT_SECRET")
        if not client_id or not secret:
            return False
        token_response = await client.post("/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=(client_id, secret))
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        names = ("paypal-auth-algo", "paypal-cert-url", "paypal-transmission-id", "paypal-transmission-sig", "paypal-transmission-time")
        verification = {key.upper().replace("-", "_"): headers.get(key) for key in names}
        verification.update({"webhook_id": webhook_id, "webhook_event": event})
        response = await client.post("/v1/notifications/verify-webhook-signature", json=verification, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json().get("verification_status") == "SUCCESS"
    except (httpx.HTTPError, KeyError, ValueError):
        return False
    finally:
        if owns_client:
            await client.aclose()


async def route_event(event: dict[str, Any], on_capture: EventHandler | None = None, on_dispute: EventHandler | None = None) -> None:
    kind = str(event.get("event_type", ""))
    handler = on_capture if kind.startswith("PAYMENT.CAPTURE.") else on_dispute if kind.startswith("CUSTOMER.DISPUTE.") else None
    if handler:
        await handler(event)


async def poll_disputes(client: Any, on_dispute: EventHandler, interval: float = 60) -> None:
    while True:
        result = await client.list_disputes()
        for dispute in result.get("items", result.get("disputes", [])):
            await on_dispute(dispute)
        await asyncio.sleep(interval)


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request) -> dict[str, bool]:
    event = await request.json()
    if not await verify_webhook_signature(dict(request.headers), event):
        raise HTTPException(status_code=400, detail="Invalid PayPal webhook signature")
    await route_event(event, getattr(request.app.state, "on_capture", None), getattr(request.app.state, "on_dispute", None))
    return {"received": True}


def start_dispute_polling(app: Any, interval: float = 60) -> asyncio.Task[None] | None:
    """Start fallback only when configured; caller should cancel returned task at shutdown."""
    if os.getenv("PAYPAL_POLLING", "false").lower() not in {"1", "true", "yes", "on"}:
        return None
    client = get_paypal_client()
    if not hasattr(app.state, "on_dispute"):
        return None
    return asyncio.create_task(poll_disputes(client, app.state.on_dispute, interval))


async def stop_dispute_polling(task: asyncio.Task[None] | None) -> None:
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
