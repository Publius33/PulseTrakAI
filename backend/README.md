PulseTrak AI by PUBLIUS33™ — powerful, real-time AI monitoring and predictive analytics.

Run the backend locally:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Production (no reload):

```bash
gunicorn -k uvicorn.workers.UvicornWorker backend.app.main:app --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}
```

Health: `GET /health` (liveness)
Ready: `GET /ready` (readiness)
Ping: `GET /api/ping`
Users endpoints:

- `GET /api/users` — list users
- `POST /api/users` — create user (requires header `X-API-Key`)
- `GET /api/users/{id}` — get user
- `DELETE /api/users/{id}` — delete user (requires header `X-API-Key`)

Environment (production):

- `ENVIRONMENT=production` — enables strict checks
- `DATABASE_URL` — PostgreSQL URL (required in prod; sqlite is only for dev)
- `JWT_SECRET_KEY` — strong secret for JWT signing (required)
- `ADMIN_TOKEN` — strong admin token for admin endpoints (required)
- `STRIPE_SECRET` or `STRIPE_SECRET_KEY` — Stripe secret (required for billing)
- `STRIPE_PUBLISHABLE_KEY` — Stripe publishable key (required for billing UI)
- `STRIPE_WEBHOOK_SECRET` — webhook signing secret (recommended)
- `ENABLE_RATE_LIMIT=1` — keep rate limiting on in prod
- `SSL_REDIRECT=1` — enforce HTTPS at proxy/ingress
- `DEMO_MODE=1` — optional demo data seeding and friendly responses
- `DB_PATH` — sqlite path for dev fallback (default: `backend/data.db`)
- `API_KEY` — dev API key for protected endpoints (default: `devkey`)

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

Scheduler & ML:

- `ENABLE_SCHEDULER` — set to `1` to enable background retraining jobs (default `1`)
- Models will retrain automatically weekly or on anomaly threshold.
- Backups are stored in `/backups` and rotated every 30 days.

Start the backend the same way; scheduler launches during FastAPI startup.
