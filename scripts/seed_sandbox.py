"""Create PayPal sandbox orders, then separately capture approved ones."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.env import load_env

AMOUNTS = ("5.00", "12.00", "25.00", "40.00", "80.00")
CURRENCY = "USD"
BACKEND_DIR = PROJECT_ROOT / "backend"
ORDERS_FILE = BACKEND_DIR / "sandbox_orders.json"
DATABASE_FILE = BACKEND_DIR / "resolve.db"


def _backend_path() -> None:
    backend = str(BACKEND_DIR)
    if backend not in sys.path:
        sys.path.insert(0, backend)


def approval_link(order: dict[str, Any]) -> str:
    for link in order.get("links", []):
        if link.get("rel") in {"approve", "payer-action"} and link.get("href"):
            return str(link["href"])
    raise ValueError("PayPal response did not include an approval link")


def load_orders(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Sandbox order store must contain a JSON list")
    return data


def save_orders(path: Path, orders: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(orders, indent=2), encoding="utf-8")
    temporary_path.replace(path)


def capture_id_from(order: dict[str, Any]) -> str | None:
    for unit in order.get("purchase_units", []):
        for capture in (unit.get("payments") or {}).get("captures", []):
            if capture.get("id"):
                return str(capture["id"])
    return None


def store_case(database_path: Path, order_id: str, capture_id: str) -> None:
    """Upsert a case with its PayPal capture ID, including existing SQLite databases."""
    _backend_path()
    from app.models import Base, Case

    engine = create_engine(f"sqlite:///{database_path.resolve().as_posix()}")
    try:
        Base.metadata.create_all(engine)
        columns = {column["name"] for column in inspect(engine).get_columns("cases")}
        if "capture_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE cases ADD COLUMN capture_id VARCHAR(128)"))
        with Session(engine) as session:
            case = session.scalar(select(Case).where(Case.external_id == order_id))
            if case is None:
                case = Case(external_id=order_id, status="open", capture_id=capture_id)
                session.add(case)
            else:
                case.capture_id = capture_id
                case.status = "open"
            session.commit()
    finally:
        engine.dispose()


def print_summary(rows: list[tuple[str, str, str]]) -> None:
    print("\nOrder ID                       Amount   Status")
    print("-" * 68)
    for order_id, amount, status in rows:
        print(f"{order_id:<30} ${amount:<7} {status}")


async def create_orders(client: Any, order_file: Path = ORDERS_FILE) -> int:
    orders = load_orders(order_file)
    rows: list[tuple[str, str, str]] = []
    return_url = os.getenv("PAYPAL_RETURN_URL", "https://example.com/")
    for amount in AMOUNTS:
        response = await client.create_order({
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": CURRENCY, "value": amount}}],
            "application_context": {
                "user_action": "PAY_NOW",
                "return_url": return_url,
                "cancel_url": return_url,
            },
        })
        order_id = str(response["id"])
        link = approval_link(response)
        status = str(response.get("status", "CREATED"))
        entry = {"order_id": order_id, "amount": amount, "currency": CURRENCY, "status": status}
        orders.append(entry)
        save_orders(order_file, orders)
        rows.append((order_id, amount, status))
        print(f"Order {order_id} approval link: {link}")
    print_summary(rows)
    print(f"\nSaved order IDs to {order_file}")
    return 0


async def capture_approved_orders(
    client: Any,
    order_file: Path = ORDERS_FILE,
    database_path: Path = DATABASE_FILE,
) -> int:
    orders = load_orders(order_file)
    if not orders:
        print("No tracked orders found. Run python scripts\\seed_sandbox.py first.")
        return 1

    rows: list[tuple[str, str, str]] = []
    skipped: list[str] = []
    failures = 0
    for entry in orders:
        order_id = str(entry["order_id"])
        amount = str(entry["amount"])
        try:
            current = await client.get_order(order_id)
            paypal_status = str(current.get("status", "UNKNOWN")).upper()
            if paypal_status == "APPROVED":
                result = await client.capture_order(order_id)
                result_status = str(result.get("status", "UNKNOWN")).upper()
                capture_id = capture_id_from(result)
                if result_status == "COMPLETED" and capture_id:
                    store_case(database_path, order_id, capture_id)
                    entry.update({"status": result_status, "capture_id": capture_id})
                    rows.append((order_id, amount, result_status))
                else:
                    entry["status"] = result_status
                    rows.append((order_id, amount, f"{result_status} (capture ID missing)"))
                    failures += 1
            elif paypal_status == "COMPLETED":
                capture_id = capture_id_from(current)
                if capture_id:
                    store_case(database_path, order_id, capture_id)
                    entry.update({"status": paypal_status, "capture_id": capture_id})
                    rows.append((order_id, amount, "COMPLETED (already captured)"))
                else:
                    entry["status"] = paypal_status
                    rows.append((order_id, amount, "COMPLETED (capture ID missing)"))
                    failures += 1
            else:
                entry["status"] = paypal_status
                skipped.append(order_id)
                rows.append((order_id, amount, f"SKIPPED ({paypal_status})"))
        except Exception as error:
            entry["status"] = f"ERROR ({type(error).__name__})"
            rows.append((order_id, amount, entry["status"]))
            failures += 1
        finally:
            save_orders(order_file, orders)

    if skipped:
        print("Not approved yet; skipped: " + ", ".join(skipped))
    print_summary(rows)
    return 1 if failures else 0


async def run(capture: bool = False) -> int:
    load_env(PROJECT_ROOT / ".env")
    os.environ["MOCK_PAYPAL"] = "false"
    # This workflow explicitly creates USD orders, independent of any general currency setting.
    os.environ["PAYPAL_CURRENCY"] = CURRENCY
    _backend_path()
    from app.paypal.client import get_paypal_client

    client = get_paypal_client()
    try:
        if capture:
            return await capture_approved_orders(client)
        return await create_orders(client)
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="capture tracked orders that PayPal reports as approved")
    args = parser.parse_args()
    try:
        return asyncio.run(run(capture=args.capture))
    except KeyboardInterrupt:
        print("Cancelled")
        return 130
    except Exception as error:
        print(f"Sandbox order operation failed ({type(error).__name__})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
