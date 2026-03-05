AES-256-GCM Encryption Model — PulseTrakAI™

This document describes encryption choices and operational guidance for Stage 4 hardening.

At-rest encryption
- Use AES-256-GCM for application-level secrets when required.
- Postgres: use `pgcrypto` for row-level encryption where needed; prefer column-level encryption for sensitive fields.
- Disk volumes / RDS: rely on cloud provider-managed KMS-backed encryption (AWS KMS).

In-transit encryption
- Enforce TLS 1.2+ on all public endpoints. Terminate TLS at load balancer.
- Enforce mTLS for internal service-to-service communication for ML and backend microservices.

Key management & rotation
- Application keys for AES-GCM must be stored in Secrets Manager (production) and loaded from environment variables in the runtime (no files committed).
- Rotation policy: 90-day rotation window for symmetric keys; maintain previous keys for decryption grace period.
- Implement forced rotation triggers (compromise, expiry) and automated re-encryption flows.

pgcrypto usage
- Use `pgp_sym_encrypt` / `pgp_sym_decrypt` for fields requiring DB-side encryption.
- Manage symmetric passphrases in Secrets Manager and inject via environment variables only.

Secrets handling
- Secrets MUST NOT be committed. Local development may use `.env` loaded from `docs/.env.sample`.
- Production: secrets loaded from AWS Secrets Manager (or equivalent) and injected into container via platform secrets.

TLS / HTTPS enforcement plan
- All ingress points: require HTTPS/TLS 1.2+.
- Redirect HTTP → HTTPS at CDN or ingress controller.
- Use HSTS and secure cookies; disable insecure TLS versions.

Operational notes
- Keep audit logs for key usage and access; rotate keys in a way that preserves ability to decrypt existing data for a defined window.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
