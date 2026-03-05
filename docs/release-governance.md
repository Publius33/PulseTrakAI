# Release Governance & Deployment SOP — PulseTrakAI™

## Overview

This document defines the structured workflow for moving code from development → staging → production releases. All deployments are **automated via GitHub Actions** with explicit approval gates.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

---

## 1. Release Levels

### Level 1: Development (`dev` branch)

**Scope**: Local development, nightly CI builds, experiment branches

```
dev
├── feature/anomaly-detection
├── feature/forecast-engine
└── bugfix/latency-issue
```

**Process**:
- Continuous commits, no formal reviews required
- Nightly automated tests and builds
- Models retrain daily
- **No production impact**

---

### Level 2: Staging (`staging` branch)

**Scope**: Integration testing, integration testing, load testing, real data exploration

```
staging
  ↑ (PR from feature branches or dev)
  └─→ Automated: CI passes, ML validates, 3-5 day soak
```

**Process**:
- Create PR from feature branch to `staging`
- **Approval gates**:
  - ✅ All CI tests pass (lint, unit tests, integration tests)
  - ✅ Backend builds and runs (docker-compose build)
  - ✅ ML model training completes with accuracy ≥ 0.88
  - ✅ Code review approval (≥1 team member)
  - ✅ No breaking schema changes

- Auto-deployed to staging environment on PR merge
- Monitored for 3-5 days: latency, error rate, anomaly quality
- **No real customer traffic, but uses real metric data samples**

---

### Level 3: Production (`v*.*.*` semantic version tags)

**Scope**: Customer-facing, real production traffic

```
v1.0.0 → v1.0.1 (patch)      # Bug fixes
      → v1.1.0 (minor)       # Features, non-breaking
      → v2.0.0 (major)       # Breaking changes
```

**Process**:
- Create release PR from staged code
- **Final approval gates**:
  - ✅ Staging soak period complete (≥3 days)
  - ✅ All production readiness checks
  - ✅ ML model signed off by Data Science team
  - ✅ Release manager approval (must be maintainer)
  - ✅ Changelog generated
  - ✅ Security review (no hardcoded secrets, no vulnerabilities)

- Merge to main, create signed v*.*.* tag
- GitHub Actions auto-deploys with blue/green strategy
- Automatic rollback on health check failure

---

## 2. Git Workflow

```
┌─────────────────────────────────────────────────────┐
│  main (always production-ready, tagged)             │ ← v1.2.3
└─────────────────────────────────────────────────────┘
                       ↑
                   (merge after approval)
                       ↑
┌─────────────────────────────────────────────────────┐
│  staging (integration testing, real data)           │
└─────────────────────────────────────────────────────┘
                       ↑ (PR merge)
                       
┌─────────────────────────────────────────────────────┐
│  dev (daily commits, fast iteration)                │
└─────────────────────────────────────────────────────┘
  ↑              ↑               ↑
feature/X   feature/Y       feature/Z
```

---

## 3. Release Checklist

### 3.1 Pre-Release (Staging phase)

**By: Data Science Team** (before release PR):
- [ ] Model trained on latest data (≥7 days old for staleness)
- [ ] Validation accuracy ≥ 0.88 on holdout test set
- [ ] No significant drift vs previous version (< 2% accuracy delta)
- [ ] Latency p99 < 500ms over 1k predictions
- [ ] False positive rate < 20% on validation set

**By: Backend Team**:
- [ ] All tests pass (`pytest tests/`)
- [ ] Linting passes (`pylint backend/`)
- [ ] Docker images build successfully
- [ ] No console errors in logs
- [ ] Health check endpoints respond correctly

**By: DevOps Team**:
- [ ] Staging deployment stable for ≥3 days
- [ ] Prometheus metrics show normal patterns
- [ ] Grafana dashboards rendering correctly
- [ ] No OOM or CPU throttling events
- [ ] Database connection pool healthy

---

### 3.2 Release PR (main)

**Open PR**: `release/v1.2.3` → `main`

**PR Template**:
```markdown
## Release v1.2.3

### Changes
- Feature: Anomaly detection improvement (PR #123)
- Bugfix: Forecast latency issue (PR #125)

### Validation Results
- ✅ 42/42 tests passing
- ✅ Model accuracy: 0.924 (was 0.918)
- ✅ Deployment staging soak: 5 days
- ✅ No regressions detected

### Approval Signoffs
- [ ] @data-science-lead: Model sign-off
- [ ] @backend-lead: Code review
- [ ] @devops-lead: Infrastructure readiness
- [ ] @release-manager: Final approval

### Rollback Plan
- Rollback command: `kubectl set image deployment/pulsetrakai-ml pulsetrakai-ml=pulsetrakai:v1.2.2-ml`
- Estimated time: < 5 minutes
- Backup location: `/backups/model_backup_20240115_143000.pkl`
```

---

### 3.3 Post-Release (Production phase)

**Immediately After Deployment**:
- [ ] Blue/Green traffic switch complete
- [ ] Health checks passing on all pods
- [ ] No alerts triggered
- [ ] Prediction latency p99 < 500ms
- [ ] Error rate < 0.1%

**First Hour**:
- [ ] Monitor Prometheus dashboard
- [ ] Check Grafana anomaly detection patterns
- [ ] Scan Loki logs for errors
- [ ] Verify database performance

**First Day**:
- [ ] Confirm no rollback triggered
- [ ] Compare metrics vs previous version
- [ ] Monitor customer support tickets
- [ ] Run post-deployment tests

---

## 4. Version Numbering (Semantic Versioning)

### MAJOR.MINOR.PATCH (e.g., v1.2.3)

**MAJOR** (v2.0.0): Breaking changes
- Database schema changes
- API endpoint removal or behavior change
- Model architecture change (incompatible with old data)
- Requires data migration

**MINOR** (v1.3.0): New features, non-breaking
- New API endpoints
- New model improvements (backward compatible)
- Performance enhancements
- New dashboard visual

**PATCH** (v1.2.5): Bug fixes, security patches
- Latency fixes
- Memory leak fixes
- Security patches
- Documentation fixes

---

## 5. Branching Strategy

```yaml
main:
  - Protected branch
  - Only accepts PRs from release/* branches
  - Requires 1 approval + CI passing
  - Auto-tags and deploys on merge

staging:
  - Accepts PRs from feature/* and bugfix/* branches
  - Requires 1 approval + CI passing + ML validation
  - Auto-deploys on merge
  - 3-5 day soak before promoting to release/*

dev:
  - Default branch
  - Anyone can push
  - Nightly CI runs
  - Feature branches cut from here
```

---

## 6. Automated Approval Gates

### Gate 1: CI Pipeline (`ci-build.yml`)

**Triggered**: On every push to dev, staging, main

```yaml
Jobs:
  - Install dependencies (Python, Node)
  - Run unit tests (pytest)
  - Run linting (pylint, flake8)
  - Build Docker images
  - Run smoke tests (docker-compose)
```

**Failure = PR cannot merge**

---

### Gate 2: ML Validation (`ml-retrain.yml`)

**Triggered**: Weekly on staging, before release tag

```yaml
Jobs:
  - Load metric data (last 30 days)
  - Train new LSTM model
  - Validate accuracy ≥ 0.88
  - Compare with baseline (< 2% regression)
  - Log results to Prometheus
```

**Failure = Release blocked until model retrains**

---

### Gate 3: Production Readiness

**Checklist in release PR**:
- [ ] ≥3 days staging soak completed
- [ ] Data science team sign-off
- [ ] DevOps team sign-off
- [ ] Release manager approval (senior engineer)
- [ ] Security review (scan for secrets)

---

## 7. Emergency Hotfix Process

**For critical production bugs**:

```
1. Create hotfix branch from main:
   git checkout -b hotfix/critical-bug

2. Fix the bug locally

3. Tag immediately (skip staging if critical):
   git tag -a v1.2.4-hotfix -m "Hotfix: critical bug"

4. Requires senior engineer approval

5. Deploy to production  

6. Merge back to dev via PR
```

**Example**: Memory leak causing pod crashes

```
hotfix/memory-leak
├─ Identified in production logs
├─ Fixed in code
├─ Tag: v1.2.2-hotfix (skip v1.2.3)
├─ Deploy in < 15 min
├─ Monitor for 30 min
└─ Post-mortem in docs/incidents/
```

---

## 8. Rollback Decision Tree

```
Production alert triggered?
├─ YES: Error rate > 2% or Latency p99 > 800ms
│   └─ Automatic rollback (< 5 minutes)
│
├─ MAYBE: Non-critical issue detected
│   ├─ Investigate logs (5-10 min)
│   ├─ If clear root cause = rollback
│   └─ If unclear = let run, monitor
│
└─ NO: Deployment stable
    └─ Continue normal operations
```

**Rollback command**:
```bash
curl -X POST https://api.pulsetrakai.com/api/admin/rollback-model \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"version": 2}'
```

---

## 9. Release Cadence

| Cadence | Type | Frequency | SLA |
|---------|------|-----------|-----|
| **Patch** | Bug fixes, security | As needed | < 24 hours |
| **Minor** | Features | Weekly | Tuesday 10 AM UTC |
| **Major** | Breaking changes | Monthly | 1st Tuesday of month |

**Example calendar**:
```
Week 1:  Minor release (v1.3.0) - Tuesday
Week 2:  Hotfixes only
Week 3:  Minor release (v1.4.0) - Tuesday
Week 4:  Major release (v2.0.0) - Tuesday
```

---

## 10. Post-Deployment Validation

### 10.1 Automated Validation

```yaml
Tests run immediately after deploy:
  - Health checks on /health, /api/pulse-horizon
  - Smoke tests: 10 prediction requests
  - Latency benchmark: p99 < 500ms
  - Error rate check: < 0.1%
  - Database connectivity check
```

### 10.2 Manual Handoff

```
QA Engineer checks:
  - Dashboard UI renders correctly
  - API rate limiting not triggered
  - Alerts fire normally
  - Billing calculations accurate
  - Customer-specific features working
```

---

## 11. Communication

**Release Announcement**:
```
@channel: Release v1.2.3 deployed to production
- Models improved anomaly detection 3% accuracy
- Fixed web dashboard latency issue
- Expected impact: better detection quality
- Status: Live. Monitoring alerts active.
```

**During incident**:
```
@incident-responders: Production issue in v1.2.3
- Symptom: Elevated error rate on /api/pulse-horizon
- Action: Initiating automatic rollback to v1.2.2
- ETA: 2 minutes
- Slack: #incidents channel updates
```

---

## 12. References

- GitHub Actions: [.github/workflows/](.github/workflows/)
- Deployment strategy: [ML Deployment Strategy](./ml-deployment-strategy.md)
- Model backup policy: [Model Backup Policy](./model-backup-policy.md)
- Cost control: [Cost Control](./infra/cost-control.md)

---

**Owner**: Release Manager & DevOps Lead
**Last Updated**: 2024
**Review Cadence**: Quarterly
