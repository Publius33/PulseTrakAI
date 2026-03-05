# PulseTrakAI Deployment Checklist

Backend (FastAPI/Gunicorn)
- Set ENVIRONMENT=production
- Set DATABASE_URL (PostgreSQL), JWT_SECRET_KEY, ADMIN_TOKEN
- Set STRIPE_SECRET or STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
- Keep ENABLE_RATE_LIMIT=1, SSL_REDIRECT=1; optional DEMO_MODE=1 for seeded data
- Start: `gunicorn -k uvicorn.workers.UvicornWorker backend.app.main:app --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}`
- Health probes: `GET /health` (liveness), `GET /ready` (readiness)

Frontend (Vite)
- Set VITE_API_BASE_URL (e.g., https://api.pulsetrak.ai)
- Optional VITE_DEMO_MODE=1 to show demo banner
- Build: `npm install` then `npm run build` (or `npm run dev` for local)

Security and ops
- Enforce HTTPS at ingress/proxy; redirect HTTP→HTTPS
- Confirm production checks pass on startup logs
- Rotate secrets regularly; disable --reload in prod
- Monitor rate-limit logs and scheduler jobs

Post-deploy smoke
- Hit /health and /ready
- Load frontend, confirm page_view analytics POST succeeds
- Run admin login + metrics list, and download billing CSV
- Trigger prediction endpoint (/api/pulse-horizon) and verify response
