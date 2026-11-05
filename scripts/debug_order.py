"""Create one PayPal sandbox order and print a limited, non-secret summary."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.env import load_env


def approval_link(order: dict[str, Any]) -> str:
    for link in order.get("links", []):
        if link.get("rel") in {"approve", "payer-action"} and link.get("href"):
            return str(link["href"])
    raise ValueError("approval link missing")


async def create_debug_order(client: Any) -> dict[str, Any]:
    currency = os.getenv("PAYPAL_CURRENCY", "USD").strip().upper() or "USD"
    return_url = os.getenv("PAYPAL_RETURN_URL", "https://example.com/")
    return await client.create_order({
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": currency, "value": "5.00"}}],
        "application_context": {
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": return_url,
        },
    })


def print_order_summary(order: dict[str, Any], requested_currency: str = "USD", requested_amount: str = "5.00") -> None:
    units = order.get("purchase_units") or []
    unit = units[0] if units else {}
    amount = unit.get("amount") or {}
    payee = unit.get("payee") or {}
    print(f"Currency: {amount.get('currency_code') or requested_currency}")
    print(f"Amount: {amount.get('value') or requested_amount}")
    print(f"Payee email: {payee.get('email_address') or 'not returned'}")
    print(f"Payee merchant ID: {payee.get('merchant_id') or 'not returned'}")
    print(f"Approval link: {approval_link(order)}")


async def run() -> int:
    load_env(PROJECT_ROOT / ".env")
    os.environ["MOCK_PAYPAL"] = "false"
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    from app.paypal.client import get_paypal_client

    client = get_paypal_client()
    try:
        currency = os.getenv("PAYPAL_CURRENCY", "USD").strip().upper() or "USD"
        order = await create_debug_order(client)
        print_order_summary(order, requested_currency=currency)
        return 0
    finally:
        await client.close()


def main() -> int:
    try:
        return asyncio.run(run())
    except Exception:
        # Keep diagnostics intentionally generic; never dump HTTP bodies or credentials.
        print("Order creation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
