# Production Hardening Guide for PulseTrakAI™

## Overview

This document describes the security hardening applied to PulseTrakAI™ for production deployment. All components have been enhanced to meet SOC2 compliance requirements and enterprise security standards.

**© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.**

---

## 1. Authentication & Authorization

### JWT Token System

**File**: `backend/app/auth/jwt_manager.py`

- **Access Tokens**: 15-minute expiry, signed with HS256
- **Refresh Tokens**: 7-day expiry, single-use rotation
- **Token Verification**: Validates signature, expiry, JTI
- **Refresh Flow**: Client presents refresh token → server generates new access token → revokes old refresh token

**Key Dates**:
- Access token invalid after 15 minutes
- Refresh token single-use (rotates on each refresh)
- Claims include: `sub` (user_id), `exp`, `iat`, `jti` (JWT ID for revocation tracking)

### Role-Based Access Control (RBAC)

**File**: `backend/app/auth/rbac.py`

**Roles**:
- `user`: Standard subscription customer, can view own metrics
- `admin`: Internal staff, can manage users, billing, configurations
- `system`: Automated processes, can trigger retraining, backups

**Permissions** (11 total):
- `read_metrics`: Query metric history
- `write_metrics`: Submit new metrics
- `read_predictions`: Get anomaly/forecast predictions
- `read_audit_logs`: View audit trail
- `manage_users`: CRUD user accounts
- `manage_models`: Reload/rollback ML models
- `manage_subscriptions`: Cancel/upgrade subscriptions
- `manage_api_keys`: Create/revoke API keys
- `view_analytics`: Dashboard access
- `admin_config`: Change system settings
- `trigger_retraining`: Force model retraining

**Enforcement**:
- FastAPI dependency injection with `require_permission()` and `require_role()` decorators
- Missing permissions → 403 Forbidden response
- All endpoints protected (deny-by-default)

### API Key Management

**File**: `backend/app/auth/rbac.py` — `APIKeyManager` class

- **Hashing**: Argon2id (memory-hard, resistant to GPU attacks) or bcrypt fallback
- **Key Format**: Prefix_UUID (e.g., `pta_abc123...`)
- **Storage**: Only bcrypt/argon2 hashes stored, plaintext keys shown once at creation
- **Rotation**: Old keys automatically revoked after 7 days

### Token Rotation & Revocation

**File**: `backend/app/auth/token_rotation.py`

- **JTI Tracking**: Every token has unique JWT ID
- **Revocation List**: In-memory (dev) or Redis-backed (production)
- **Rotation History**: Tracks user token rotation patterns
- **Suspicious Pattern Detection**: 
  - >3 rotations in 5-minute window → security alert
  - Automatic suspend if pattern detected
- **Cleanup**: Revocation list pruned every 24 hours (removes expired tokens)

---

## 2. Input Validation & Data Sanitization

### Metric Validation

**File**: `backend/app/schemas/metric_schema.py`

**MetricEventSchema** (single event):
- `metric_name`: 1-128 characters, alphanumeric + underscore only
- `value`: ±1e10 bounds (prevents overflow)
- `timestamp`: Must be in past (rejects future timestamps)
- `source`: Max 128 characters, alphanumeric
- `tags`: Max 10 tags, key-value pairs, max 128 chars each

**MetricsPayloadSchema** (batch):
- Max 1,000 metrics per request
- Consistent schema validation for each metric

**MetricQuerySchema** (data retrieval):
- Max query limit: 10,000 records
- Time range bounds (prevents table scans on unbounded queries)
- Source filter whitelist validation

### Prediction Validation

**File**: `backend/app/schemas/prediction_schema.py`

**PredictionRequestSchema**:
- `metric_name`: Validated per MetricEventSchema rules
- `features`: 1-1,000 numeric values
- `feature_values`: ±1e10 bounds
- `lookback_days`: 1-365 (prevents excessive memory usage)
- `confidence_threshold`: 0-1, inclusive

**AnomalyPredictionSchema** (response):
- `is_anomaly`: Boolean
- `anomaly_score`: 0-1 (confidence)
- `predicted_threshold`: Threshold used for classification
- `explanation`: Human-readable reasoning

**ForecastPredictionSchema**:
- `forecast_values`: Array of predicted values
- `timestamps`: Corresponding prediction timestamps
- `confidence_bounds`: [lower, upper] 95% CI bounds

### Validation Features

- **Pydantic v2**: Type checking at request boundary
- **Field Constraints**: Min/max values, string lengths
- **Custom Validators**: Timestamp bounds, format validation
- **Unknown Fields**: Rejected (extra="forbid") to prevent injection
- **Coercion**: Types coerced to expected (float → int OK, string → float NOT OK)

---

## 3. Database Security

### Schema & Indexing

**File**: `backend/db/migrations/002_add_indexes.sql`

**Indexes Created**:
1. `metric_events(timestamp DESC)` — Latest metrics queries
2. `metric_events(source)` — Filter by data source
3. `pulse_predictions(generated_at DESC)` — Recent predictions
4. `users(username)` — Login lookups
5. `audit_logs(created_at DESC)` — Audit trail access
6. `audit_logs(user_id)` — User activity tracking
7. `audit_logs(action)` — Action-based auditing
8. `subscription_events(created_at DESC)` — Billing history
9. Composite: `metric_events(metric_name, timestamp)` — Common query pattern
10. Composite: `pulse_predictions(metric_name, generated_at)` — Prediction queries

**Expected Performance**:
- Indexed queries: <2 seconds on 10M+ rows
- Full table scans prevented on common queries
- Composite indexes optimize multi-column WHERE clauses

### SQL Injection Prevention

- **Parameterized Queries**: All ORM operations use prepared statements
- **No String Concatenation**: Query building via SQLAlchemy/Pydantic, never f-strings
- **Database User**: Limited permissions (SELECT/INSERT/UPDATE, no DROP/ALTER)

### Query Limits

- Max result set: 10,000 records (prevents memory exhaustion)
- Max query time: 30 seconds (slow query logging)
- Connection pool: 5-20 connections (DOS prevention)

---

## 4. Error Handling & Logging

### Global Error Handler

**File**: `backend/app/middleware/error_handler.py`

**Behavior**:
- All exceptions caught at middleware layer
- **Client Response**: Sanitized JSON with error ID (no stack traces, no sensitive data)
- **Server Logging**: Full traceback, request details, user context

**Error Types**:
- `HTTPException` (422, 403, 401): Returns original status + message
- `ValidationError` (Pydantic): Returns 422 + field-level errors
- Generic exceptions: Returns 500 + error ID for support lookup

**Error ID Format**: `ERR-{timestamp}-{random_32bits}` (e.g., `ERR-20240115120000-a1b2c3d4`)

**Example Response**:
```json
{
  "error_id": "ERR-20240115120000-a1b2c3d4",
  "message": "Metric validation failed",
  "status": 422,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Structured Logging

**Format**: JSON with consistent fields
```json
{
  "timestamp": "2024-01-15T12:00:00.123456Z",
  "level": "INFO",
  "service": "backend",
  "event": "metric_received",
  "user_id": "user-123",
  "metric": "cpu_usage",
  "value": 45.2,
  "region": "us-east-1",
  "metadata": {"source": "prometheus", "version": "1.2.3"}
}
```

**Log Levels**:
- `DEBUG`: Development only, internal state
- `INFO`: User actions (login, metric submit, prediction request)
- `WARNING`: Anomalies (high latency, drift detected)
- `ERROR`: Failures (DB connection lost, ML model crash)
- `CRITICAL`: Startup failures, data loss risk

### Audit Logging

**File**: `backend/app/models/audit_log.py`, `backend/app/services/audit_service.py`

**Audit Actions** (23 types):
- Authentication: `login`, `logout`, `token_refresh`, `password_change`
- Models: `reload_model`, `rollback_model`, `trigger_retraining`, `model_drift_detected`
- Users: `user_created`, `user_updated`, `user_deleted`
- Subscriptions: `subscription_created`, `subscription_cancelled`, `subscription_updated`
- Billing: `payment_received`, `payment_failed`, `refund_issued`
- Admin: `admin_config_changed`, `api_key_created`, `api_key_rotated`, `api_key_revoked`

**AuditService Methods**:
- `log_action(user_id, action, resource, details, status)` — Record audit event
- `get_user_actions(user_id)` — All actions by user
- `get_action_logs(action)` — All instances of specific action
- `get_failed_actions()` — Status >= 400 (errors/denials)
- `get_admin_actions()` — Admin-only actions

**Dual-Write Strategy**:
- Events logged to database (SQLite dev / PostgreSQL prod)
- Events also output to structured logger
- Immutable audit trail (no deletes, only inserts)

---

## 5. Model Security & Drift Detection

### Model Storage

- **Persistence**: Models saved as `.pkl` + metadata JSON in `backend/ml/models/`
- **Versioning**: Timestamped checkpoints (e.g., `baseline_model_20240115_120000.pkl`)
- **Access Control**: Models loaded only by system role, not user-accessible directly
- **File Permissions**: Models stored with 0600 (owner read-write only)

### Drift Detection

**File**: `backend/ml/drift_detection.py`

**Algorithm**:
- **Baseline**: Historical metrics from past 30 days (represents expected behavior)
- **Recent**: Metrics from past 24 hours (current model context)
- **Deviation Calculation**: Standardized score (0-1 scale)
  - Formula: `|recent_mean - baseline_mean| / baseline_stdev`
  - Normalized: If deviation > 3σ (sigma), score = 1.0 (maximum)
  - Scores <0.1: No drift detected
  - Scores 0.1-0.3: Minor drift, monitor
  - Scores 0.3-0.7: Significant drift, recommend retraining
  - Scores >0.7: Severe drift, automatic retraining triggered

**DriftDetector Methods**:
- `check_drift(metric_name)` → Returns deviation 0-1
- `get_baseline_metrics(metric_name, days=30)` → Baseline statistics
- `get_recent_metrics(metric_name, hours=24)` → Current statistics
- `get_drift_report()` → All metrics with drift scores
- `detect_suspicious_rotation()` — Pattern detection analogy

**Retraining Trigger**:
- Automatic: Drift score > 0.7
- Manual: Admin can trigger via API
- Scheduled: Weekly model refresh (Sunday 2 AM UTC)

### Model Validation

- **Pre-deployment**: Unit tests on test set
- **Post-deployment**: Prediction accuracy tracked in background job
- **Rollback**: If 3 consecutive errors, automatic rollback to previous version
- **Monitoring**: Prometheus metrics exported (latency, error rate)

---

## 6. Rate Limiting & DOS Protection

### Rate Limit Configuration

**Tier 1 (Free/Trial)**:
- API requests: 100/hour
- Metric submissions: 1,000/day
- Predictions: 10/hour

**Tier 2 (Standard)**:
- API requests: 10,000/day
- Metric submissions: 100,000/day
- Predictions: 1,000/day

**Tier 3 (Enterprise)**:
- API requests: Unlimited
- Metric submissions: Unlimited
- Predictions: Unlimited

**Admin Panel**:
- API requests: 1,000/hour
- No metric/prediction limits

### Implementation

- **Backend**: FastAPI middleware using Redis or in-memory cache
- **Key Format**: `{user_id}:{endpoint}:{hour}` (sliding window)
- **Overage**: Returns 429 Too Many Requests
- **Retry-After**: Header indicates next available slot

### IP-Based Blocking

- Max 10 failed auth attempts (5 minute cooldown) → Temporary ban
- CAPTCHA triggered after 3 bans in 24 hours
- Admin whitelisting for known IPs

---

## 7. Background Worker Security

**File**: `backend/worker/worker.py`

### Queue Backend Options

1. **Redis RQ** (Primary): Distributed queue, job tracking, automatic retry
2. **Celery** (Alternative): Supports multiple brokers (Redis, RabbitMQ)
3. **InProcessQueue** (Development): Synchronous fallback for local testing

### Scheduled Tasks

**Retraining Task** (`retrain_model_task`):
- Triggered: Weekly (Sundays 2 AM UTC) or manually
- Isolation: Runs in separate process, doesn't block API
- Logging: All training steps logged (data size, model accuracy, drift scores)
- Rollback: If new model accuracy drops >5%, revert to previous

**Backup Task** (`backup_model_task`):
- Frequency: Daily (1 AM UTC)
- Destination: S3 (encrypted)
- Retention: Keep last 30 days
- Integrity: SHA256 checksum verified on restore

**Drift Detection Task** (`detect_drift_task`):
- Frequency: Every 4 hours
- Notification: Alert admin if drift > 0.5
- Logging: Drift reports stored for audit trail

**Report Generation Task** (`generate_report_task`):
- Frequency: Daily (5 AM UTC for previous day)
- Content: Metrics summary, predictions made, anomalies detected, billing events
- Distribution: Email to account owner

### Worker Access

- Workers authenticate with internal API using `SYSTEM_ROLE` token
- Workers can only write audit logs and trigger model operations
- Worker environment vars isolated from API server

---

## 8. Encryption

### In-Transit (TLS/SSL)

- **Protocol**: TLS 1.2 minimum (TLS 1.3 preferred)
- **Certificates**: Valid wildcard certificate for `*.pulsetrak.ai`
- **Cipher Suites**: ECDHE-based (forward secrecy)
- **HSTS**: Enabled, 365-day max-age
- **Certificate Pinning**: Mobile apps

### At-Rest

**Stripe Keys**:
- Encrypted in `.env.production` file
- Database: Not stored (external tokenization)

**User Passwords**:
- Bcrypt with cost factor 12 (160ms hash time)
- Salts: Unique per password
- Legacy passwords: Re-hashed on login (if using weaker algorithm)

**API Keys**:
- Argon2id hash (not reversible)
- Only plaintext key shown once at creation
- Rotation: Auto-revoke after 7 days

**Audit Logs**:
- Plaintext in database (not PII, just actions)
- Access controlled via audit_read permission

**Backups**:
- S3 server-side encryption (AES-256)
- KMS-managed keys (AWS)
- Separate backup credentials (minimal permissions)

---

## 9. Network Security

### Load Balancer (ALB/CloudFront)

- **DDoS Protection**: AWS Shield Advanced
- **WAF**: AWS WAF with managed rulesets
- **SSL/TLS**: Terminated at load balancer
- **Static Content**: Served via CloudFront CDN (geographically distributed)

### VPC Configuration

- **Private Subnets**: Database (RDS) not internet-accessible
- **NAT Gateway**: Worker/scheduler outbound through NAT (traceable IPs)
- **Security Groups**:
  - ALB: Port 443 (HTTPS) from 0.0.0.0/0
  - API: Port 8000 from ALB only
  - RDS: Port 5432 from API security group only
  - Redis: Port 6379 from API/Worker security groups only

### VPN & Bastion

- Admin access through VPN (OpenVPN) or bastion host
- SSH key-pair authentication (no password)
- Session recording for compliance

---

## 10. Compliance & Auditing

### SOC2 Type II

- **Audit Trail**: All user actions logged with timestamps, user IDs, IP addresses
- **Change Management**: Model rollbacks tracked, approval workflow enforced
- **Access Control**: Role-based permissions, regular access reviews
- **Data Retention**: Logs kept for minimum 90 days
- **Incident Response**: Automated alerts for suspicious patterns, escalation playbook

### Data Retention

- **Metrics**: Keep indefinitely (customer's sensor data)
- **Predictions**: Keep 1 year (regulatory requirement)
- **Audit Logs**: Keep 2 years (SOC2 requirement)
- **Backups**: Keep 30 days (recovery window)
- **Temporary Files**: Auto-delete after 24 hours

### Privacy

- **No Data Sharing**: Customer metrics never shared (single-tenant model)
- **Anonymization**: Training data anonymized (remove customer identifiers)
- **Data Deletion**: On account deletion, all customer data purged within 30 days
- **GDPR Compliance**: Data export on request, right-to-be-forgotten support

---

## 11. Startup Safety Checks

**File**: `backend/app/config/production_checks.py`

**Validation on Startup**:
1. Stripe secret key configured
2. Database not SQLite in production
3. JWT secret key strong (>32 chars, not default)
4. Admin token not default value
5. Rate limiting enabled in production
6. Redis available (if queues configured)
7. SSL redirect enforced in production
8. DEBUG mode disabled in production
9. Structured logging configured

**Failure Behavior**:
- In production: Exit with code 1 (crash container, trigger restart policy)
- In development: Log warnings, continue (for faster iteration)

**Monitoring**:
- Kubernetes readiness probe calls `/ready` (checks all systems)
- Liveness probe calls `/health` (basic connectivity)
- Failure of checks → pod marked as not-ready → traffic shifted to healthy pods

---

## 12. Incident Response

### Alert Thresholds

- **High Latency**: P99 > 5 seconds → Page on-call engineer
- **Error Rate**: >1% → Warn, >5% → Page
- **Model Drift**: Score >0.7 → Retrain, notify admin
- **Token Rotation**: >3 in 5 min → Suspend and alert
- **Prediction Accuracy**: Drop >5% → Rollback previous model

### Incident Playbook

1. **Database Down**:
   - Health check fails → Kubernetes shifts traffic
   - Metrics: Still in-memory cache, buffer up to 1 hour
   - Recovery: RDS auto-failover (multi-AZ), 2-3 min recovery

2. **ML Model Crash**:
   - Automatic fallback to baseline model
   - Predictions less accurate but available
   - Background task triggers retraining

3. **Stripe Integration Down**:
   - Billing endpoints return 503
   - No new subscriptions allowed (graceful degradation)
   - Existing subscriptions still active
   - Recovery: Automatic retry with exponential backoff

4. **Token Revocation List Full**:
   - Less likely (cleanup runs hourly)
   - Fallback: Check database audit_logs for JTI
   - If failed: Require token re-auth from user

5. **Data Corruption**:
   - Audit trail immutable (catches deletion)
   - Daily backups → 30-day retention
   - Recovery: Restore from backup, replay recent transactions

---

## 13. Deployment Checklist

### Pre-Production

- [ ] All environment variables set (no defaults in production)
- [ ] Database migrations applied (`python backend/db/run_migrations.py`)
- [ ] Stripe webhook configured (POST hook to `/stripe/webhook`)
- [ ] Nginx/Kubernetes manifests reviewed for security
- [ ] TLS certificates valid (not self-signed)
- [ ] Backups tested (restore procedure documented)
- [ ] Monitoring dashboards created (Prometheus/Grafana)
- [ ] Incident response playbook distributed to team
- [ ] Load testing completed (peak quota: 100k req/min)
- [ ] Security audit completed (OWASP Top 10 review)

### Post-Deployment

- [ ] Health checks passing (all pods green)
- [ ] Production tests running (CI/CD pipeline)
- [ ] Access logs being collected (S3 for audit)
- [ ] Error tracking enabled (Sentry or equivalent)
- [ ] On-call rotation activated
- [ ] Customer notification (status page update)
- [ ] Database backup running (verify restore)
- [ ] Scheduled tasks executing (worker logs)

---

## 14. References

**Related Documentation**:
- [Security Model](../security-model.md) — System-level design
- [SOC2 Checklist](../soc2-checklist.md) — Compliance requirements
- [Encryption Model](../encryption.md) — Data security details
- [Access Control](../soc2/access-control.md) — User management
- [Incident Response](../soc2/incident-response.md) — Procedures
- [Change Management](../soc2/change-management.md) — Deployment workflow

**External Standards**:
- OWASP Top 10 (https://owasp.org/Top10/)
- JWT Best Practices (https://tools.ietf.org/html/rfc8725)
- SOC2 Trust Service Criteria (https://www.aicpa.org/soc2)

---

**Last Updated**: January 15, 2024  
**Version**: 1.0  
**Status**: Production  
**Owner**: Security Team
