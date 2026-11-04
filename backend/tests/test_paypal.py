import asyncio

import httpx
import pytest
from scripts import check_paypal as check_paypal_script

from app.paypal.auth import PayPalAuth
from app.paypal.client import MockPayPalClient, PayPalClient, get_paypal_client
from app.paypal.disputes import Disputes
from app.paypal.orders import Orders
from app.paypal.webhooks import poll_disputes, route_event, verify_webhook_signature


@pytest.mark.asyncio
async def test_oauth_token_cached_until_expiry(monkeypatch):
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})

    http = httpx.AsyncClient(base_url="https://api-m.sandbox.paypal.com", transport=httpx.MockTransport(handler))
    auth = PayPalAuth(http)
    assert await auth.get_token() == await auth.get_token() == "token"
    assert len(calls) == 1
    auth._token.expires_at = 0
    assert await auth.get_token() == "token"
    assert len(calls) == 2
    await http.aclose()


@pytest.mark.asyncio
async def test_orders_and_disputes_use_sandbox_http(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "secret-token", "expires_in": 3600})
        return httpx.Response(200, json={"id": "A1", "status": "COMPLETED"})

    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    http = httpx.AsyncClient(base_url="https://api-m.sandbox.paypal.com", transport=httpx.MockTransport(handler))
    client = PayPalClient(http)
    assert (await client.create_order({"intent": "CAPTURE"})) ["id"] == "A1"
    assert (await client.capture_order("A1"))["status"] == "COMPLETED"
    assert (await client.list_disputes())["id"] == "A1"
    assert calls[1].url.path == "/v2/checkout/orders"
    assert calls[2].url.path == "/v2/checkout/orders/A1/capture"
    assert calls[3].url.path == "/v1/customer/disputes"
    assert calls[1].headers["authorization"] == "Bearer secret-token"
    await http.aclose()


@pytest.mark.asyncio
async def test_dispute_write_paths_and_payloads(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(200, json={"status": "OK"})

    monkeypatch.setenv("PAYPAL_CLIENT_ID", "c")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "s")
    http = httpx.AsyncClient(base_url="https://api-m.sandbox.paypal.com", transport=httpx.MockTransport(handler))
    client = PayPalClient(http)
    await client.get_dispute("D1")
    await client.provide_evidence("D1", {"evidence": []})
    await client.make_offer("D1", {"note": "offer"})
    await client.accept_claim("D1")
    await client.send_message("D1", {"message": "hello"})
    assert [request.url.path for request in calls[1:]] == [
        "/v1/customer/disputes/D1", "/v1/customer/disputes/D1/provide-evidence",
        "/v1/customer/disputes/D1/make-offer", "/v1/customer/disputes/D1/accept-claim",
        "/v1/customer/disputes/D1/send-message",
    ]
    await http.aclose()


def test_mock_paypal_selection_and_surface(monkeypatch):
    monkeypatch.setenv("MOCK_PAYPAL", "true")
    client = get_paypal_client()
    assert isinstance(client, MockPayPalClient)
    assert all(hasattr(client, name) for name in ("create_order", "capture_order", "list_disputes", "get_dispute", "provide_evidence", "make_offer", "accept_claim", "send_message"))


@pytest.mark.asyncio
async def test_webhook_verification_and_routing(monkeypatch):
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "hook")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "c")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "s")
    def handler(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t"})
        assert request.url.path.endswith("/verify-webhook-signature")
        assert request.read().find(b"hook") >= 0
        return httpx.Response(200, json={"verification_status": "SUCCESS"})
    http = httpx.AsyncClient(base_url="https://api-m.sandbox.paypal.com", transport=httpx.MockTransport(handler))
    assert await verify_webhook_signature({"paypal-auth-algo": "a"}, {"event_type": "PAYMENT.CAPTURE.COMPLETED"}, http)
    hit = []
    async def capture(event): hit.append(event["event_type"])
    async def dispute(event): hit.append(event["event_type"])
    await route_event({"event_type": "PAYMENT.CAPTURE.COMPLETED"}, capture, dispute)
    await route_event({"event_type": "CUSTOMER.DISPUTE.CREATED"}, capture, dispute)
    assert hit == ["PAYMENT.CAPTURE.COMPLETED", "CUSTOMER.DISPUTE.CREATED"]
    await http.aclose()


@pytest.mark.asyncio
async def test_polling_disputes_once_then_cancels():
    seen = []
    class Client:
        async def list_disputes(self): return {"items": [{"id": "D1"}]}
    async def handler(dispute):
        seen.append(dispute["id"])
        raise asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await poll_disputes(Client(), handler, interval=60)
    assert seen == ["D1"]


@pytest.mark.asyncio
async def test_auth_check_forces_real_client_and_prints_only_success(monkeypatch, capsys):
    class Auth:
        async def get_token(self):
            assert __import__("os").environ["MOCK_PAYPAL"] == "false"
            return "must-not-be-printed"
    class Client:
        auth = Auth()
        async def close(self): pass
    monkeypatch.setattr(check_paypal_script, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.paypal.client.get_paypal_client", lambda: Client())
    assert await check_paypal_script.check() == 0
    assert capsys.readouterr().out.strip() == "PayPal sandbox auth OK"


@pytest.mark.asyncio
async def test_auth_check_prints_only_error_type(monkeypatch, capsys):
    class Auth:
        async def get_token(self): raise RuntimeError("secret token and credentials")
    class Client:
        auth = Auth()
        async def close(self): pass
    monkeypatch.setattr(check_paypal_script, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.paypal.client.get_paypal_client", lambda: Client())
    assert await check_paypal_script.check() == 1
    assert capsys.readouterr().out.strip() == "RuntimeError"
