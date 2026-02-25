Run the backend locally:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET /health`
Ping: `GET /api/ping`
Users endpoints:

- `GET /api/users` — list users
- `POST /api/users` — create user (requires header `X-API-Key`)
- `GET /api/users/{id}` — get user
- `DELETE /api/users/{id}` — delete user (requires header `X-API-Key`)

Environment:

- `API_KEY` — API key required for protected endpoints (default: `devkey`)
- `DB_PATH` — path to sqlite DB file (default: `backend/data.db`)

Analytics endpoints (opt-in):

- `POST /api/analytics/track` — track an anonymous event. JSON body: `{"event":"page_view"}`
- `GET /api/metrics` — list aggregated metrics (event, count, last_ts)

Payments (Stripe)

- `POST /api/payment/create-intent` — create a Stripe PaymentIntent. JSON: `{"amount_cents": 500, "currency":"usd"}`. Requires `STRIPE_SECRET` in env.
- `POST /api/payment/webhook` — Stripe webhook endpoint. Set `STRIPE_WEBHOOK_SECRET` to enable signature verification.

Environment settings:

- `STRIPE_SECRET` — your Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — the webhook signing secret for verifying events
