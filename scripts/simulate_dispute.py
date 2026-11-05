"""List disputes currently visible in the PayPal sandbox account."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.env import load_env


def _project_root() -> Path:
    root = PROJECT_ROOT
    backend = str(root / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    return root


def print_disputes(result: dict[str, Any]) -> int:
    disputes = result.get("items", result.get("disputes", []))
    if not disputes:
        print("No sandbox disputes found")
        return 0
    for dispute in disputes:
        dispute_id = dispute.get("dispute_id", dispute.get("id", "unknown"))
        status = dispute.get("status", "unknown")
        reason = dispute.get("reason", "unknown")
        print(f"{dispute_id}: status={status}, reason={reason}")
    return len(disputes)


async def run() -> int:
    root = _project_root()
    load_env(root / ".env")
    os.environ["MOCK_PAYPAL"] = "false"
    from app.paypal.client import get_paypal_client

    client = get_paypal_client()
    try:
        return print_disputes(await client.list_disputes())
    finally:
        await client.close()


def main() -> int:
    try:
        return asyncio.run(run())
    except Exception as error:
        print(f"Sandbox dispute lookup failed ({type(error).__name__})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
