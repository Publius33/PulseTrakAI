PulseTrak AI by PUBLIUS33™ — powerful, real-time AI monitoring and predictive analytics.

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

- `GET /api/stripe/config` — returns `publishable_key` and `ready` flag so the frontend can load Stripe Elements.

Client-side integration notes:

- `STRIPE_PUBLISHABLE_KEY` — set this in your backend env and the frontend will fetch it from `/api/stripe/config`.
- Typical flow: create a PaymentIntent via `/api/payment/create-intent`, confirm payment client-side with Stripe Elements, then create a subscription via `/api/subscriptions`.

Environment settings:

- `STRIPE_SECRET` — your Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — the webhook signing secret for verifying events
