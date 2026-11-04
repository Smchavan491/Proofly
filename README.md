# Resolve

Resolve is a starter project for a PayPal merchant dispute response dashboard. It includes a FastAPI health endpoint, initial SQLAlchemy table definitions, a placeholder React dashboard, and an async PayPal client for sandbox orders and disputes. Webhook events are verified by PayPal before capture and dispute handlers are called. A polling fallback can check disputes every 60 seconds.

## Development

Use Python 3.12. Create the virtual environment in the project root, activate it, and install the backend requirements.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pytest backend\tests
```

### macOS

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests
```

### Linux

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests
```

After installation, start the backend from the project root with `make run`, or run `.venv`'s Python directly:

```sh
python -m uvicorn --app-dir backend app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; health check: `/health`.

## PayPal sandbox

Set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in the environment to use the sandbox API at `https://api-m.sandbox.paypal.com`. The client caches OAuth tokens until shortly before expiry. `MOCK_PAYPAL` defaults to `true`; set it to `false` to use PayPal's sandbox. Mock mode keeps order state in memory and does not contact PayPal.

For signed webhook delivery, set `PAYPAL_WEBHOOK_ID` to the webhook ID configured in the PayPal sandbox. The receiver is `POST /webhooks/paypal`. Application code can assign async `on_capture` and `on_dispute` handlers on `app.state` to process verified events. Set `PAYPAL_POLLING=true` and provide `app.state.on_dispute` to enable the 60-second dispute polling fallback. Writes are exposed as explicit client methods; callers must keep them behind the application's approval workflow.

Start the web dashboard with `npm install` once from `web`, then `npm run dev` from `web` (or `make web` from the project root).
