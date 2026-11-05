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

### Seed sandbox orders and inspect disputes

1. Put `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in the project-root `.env` file. These must be PayPal sandbox app credentials. The scripts force `MOCK_PAYPAL=false` and never display credentials or OAuth tokens. Set `PAYPAL_CURRENCY` to the currency accepted by the sandbox business account; it defaults to `USD`. You may set `PAYPAL_RETURN_URL` to the URL buyers should return to after approving or cancelling; it defaults to `https://example.com/` for this manual sandbox workflow.
2. From the project root, run `python scripts\seed_sandbox.py`. It creates five USD orders ($5.00, $12.50, $25.00, $50.00, and $100.00) and prints each sandbox approval link.
3. Open every approval link in a private browser window, sign in with a sandbox personal/buyer account, and approve the order. Return to the terminal and press Enter. The script captures each order and stores successfully completed orders as open cases in `backend/resolve.db`. If an order has not been approved, its capture is reported as failed and it is not stored as a case.
4. To list disputes already present in the sandbox account, run `python scripts\simulate_dispute.py`. This script lists disputes; it does not create a simulated PayPal dispute.

To create one diagnostic sandbox order and print its currency, amount, payee email, payee merchant ID, and approval link, run `python scripts\debug_order.py`. The script does not capture the order. It prints `not returned` when PayPal omits a payee field.

PayPal order creation and capture are live sandbox requests. Case records are stored locally in SQLite; no production PayPal account or database is used.

Start the web dashboard with `npm install` once from `web`, then `npm run dev` from `web` (or `make web` from the project root).
