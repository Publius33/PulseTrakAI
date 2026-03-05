© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

# PulseTrakAI™ Security Model (Stage 3)

Purpose: outline the enterprise-grade security posture for Stage 3.

Data isolation by tenant
- Row-level ownership: every tenant-scoped table MUST include `account_id` or `owner_id`.
- Queries must always apply tenant filters; use prepared statements and parameterized queries.

Authentication
- API key authentication: per-user API keys allowed via `X-API-Key` or `Authorization: Bearer`.
- Keys must be stored hashed (bcrypt/argon2) and rotated via admin console.

JWT auth with rotation + signing key rollover
- Use short-lived JWTs (e.g. 1 hour). Maintain a key-rotation schedule (30-day rotation recommended).
- Support verification of previous keys for a grace window during rollover.

Encrypted secrets
- Production: AWS Secrets Manager for all secrets. Use least-privilege IAM roles for access.
- Local: `.env` files allowed for development. Provide `docs/.env.sample` as guidance.

Transport security
- Enforce TLS 1.2+ for all external endpoints.
- Internal service-to-service traffic uses mTLS and mutual authentication.

PII and data minimization
- Store no personal information except `email` (for billing/contacts) and `billing_id` when necessary.
- Do not store session keystrokes or detailed behavior logs.

Access control levels
- `user` — tenant-level access
- `admin` — organization or system administrator
- `system` — ML/internal services (machine identity, mTLS or signed service tokens)

Rate limiting & IP throttling
- Route limits implemented in backend middleware (Stage 3):
  - `POST /api/metrics` → 100 req/sec per IP
  - `/api/pulse-horizon` → 5 req/sec per user (API Key / Authorization)
  - `/api/recommendations` → 3 req/sec per user
- Global IP throttling to mitigate abuse.

Audit & logging
- Record authentication, admin actions, and billing events to an immutable audit store.
- Retain logs for a minimum of 90 days (see SOC2 checklist).

Operational notes
- Rotate secrets and keys periodically. Automate rotation where possible and maintain revocation lists.

Refer to `/infrastructure` and `/infrastructure/k8s` for deployment-level controls and mTLS guidance.
# Security Model

PulseTrakAI™ Security Model

• Data isolation by tenant: row-level ownership enforced in DB queries and application logic. All reads/writes include tenant scoping keys and `WHERE tenant_id = ?` guards.

• API key authentication per user: short-lived API keys issued per user, stored hashed, rotated on demand.

• JWT auth with rotation + signing key rollover: use asymmetric keys (RSA or ECDSA) with key IDs (kid) in JWT headers. Support key rollover and 30-day rotation schedule.

• Encrypted secrets:
  - production: use AWS Secrets Manager for STRIPE keys, DB credentials, and JWT keys.
  - local: use a `.env` file with sample `.env.sample` checked into repo (no secrets).

• TLS 1.2+ everywhere (enforce TLS in load balancer, API Gateway, and internal services).

• Zero PII: store only email and billing id. No other personal data is persisted. Sensitive fields must be redacted in logs.

• Access control levels:
  - `user` — regular account operations
  - `admin` — administrative operations (create plans, run analytics)
  - `system` — internal system components (ML workers, cron)

Rate limiting and IP throttling

• Per-route limits implemented in backend middleware (in-memory token buckets for demo). Replace with distributed limiter (Redis, API Gateway) for production.

• Configured limits:
  - `POST /api/metrics` → 100 req/sec (per IP)
  - `/api/pulse-horizon` → 5 req/sec per user (API key or auth token)
  - `/api/recommendations` → 3 req/sec per user

• IP throttling middleware enforced globally: default 300 req/sec per IP.

Audit logging & monitoring

• All auth events (token issuance, key rotation), billing events, and admin actions are logged to an immutable audit stream (WORM S3 or dedicated DB) and sent to SIEM.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
