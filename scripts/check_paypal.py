"""Check PayPal sandbox OAuth without exposing credentials or token values."""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.env import load_env


async def check() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_env(project_root / ".env")
    backend_path = str(project_root / "backend")
    if backend_path not in os.sys.path:
        os.sys.path.insert(0, backend_path)
    # This utility is specifically intended to validate real sandbox credentials.
    os.environ["MOCK_PAYPAL"] = "false"

    from app.paypal.client import get_paypal_client

    client = get_paypal_client()
    try:
        await client.auth.get_token()
        print("PayPal sandbox auth OK")
        return 0
    except Exception as error:
        print(type(error).__name__)
        return 1
    finally:
        await client.close()


def main() -> int:
    try:
        return asyncio.run(check())
    except Exception as error:
        # Keep failures limited to the exception class; never render exception text.
        print(type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
