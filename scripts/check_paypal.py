"""Check PayPal sandbox OAuth without exposing credentials or token values."""

import asyncio
import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Load basic KEY=VALUE entries without replacing variables already set."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key or not key.replace("_", "a").isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


async def check() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
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
