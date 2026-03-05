# ML Model Deployment Strategy — PulseTrakAI™

## Overview

This document defines the process for safely deploying new ML model versions to production using a **Blue/Green** strategy with **canary testing** and automated rollback capabilities.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

---

## 1. Deployment Stages

### 1.1 Development (dev branch)

**Purpose**: Continuous training and testing on developers' machines.

- Daily model retraining on fresh metric data
- Automated unit tests for feature extraction and LSTM validation
- No production traffic
- Models stored in `/models/dev/` directory

**Validation Gates**:
- ✅ Training pipeline completes without errors
- ✅ Model validation accuracy ≥ 0.88
- ✅ No memory leaks or hanging processes

---

### 1.2 Staging (staging branch)

**Purpose**: Integration testing with realistic load and data.

- Deploy latest model from dev to staging cluster
- Run against 7-day sample of real metric data
- Full observability: Prometheus, Grafana, Loki logs
- Simulate production traffic patterns (100 concurrent predictions/sec)

**Validation Gates**:
- ✅ Prediction latency p99 < 500ms
- ✅ No significant accuracy regression (< 2% delta)
- ✅ CPU usage stable at low load
- ✅ Error rate < 0.1%

**Duration**: 3-5 days before production promotion

---

### 1.3 Production (v* release tags)

**Purpose**: Serve real production traffic with high availability.

---

## 2. Blue/Green Deployment Strategy

### 2.1 Architecture

```
┌─────────────────────────────────────────┐
│  Load Balancer (AWS ALB)                │
│  - Health checks: /health, /api/pulse-horizon
│  - Sticky sessions: disabled (stateless)
└───────┬─────────────────────┬───────────┘
        │                     │
    ┌───▼────┐            ┌───▼────┐
    │ BLUE   │            │ GREEN  │
    │Pod Set │            │Pod Set │
    │(v1)    │            │(v2)    │
    └────────┘            └────────┘
        ↓                      ↓
   Traffic: 100%          Traffic: 0%
   (Active)               (Standby)
```

### 2.2 Deployment Flow

**Step 1: Pre-deployment Backup**
```
→ BackupManager.create_backup(current_model, reason="pre_deployment")
→ Save snapshot of current model to /backups/model_TIMESTAMP.pkl
```

**Step 2: Build & Push** (triggered by v*.* tag)
```
→ CI pipeline builds Docker image with new model version
→ Image tagged as: pulsetrakai:v2.1.0-ml (with model bundled)
→ Image pushed to ECR registry
```

**Step 3: Health Checks on Staging**
```
→ Deploy GREEN pods with new image in staging cluster
→ Wait for pod readiness probes: /health endpoint responds 200
→ Run smoke tests: POST /api/pulse-horizon with sample data
→ Verify response time p99 < 500ms
```

**Step 4: Canary Testing** (optional, configurable)
```
→ If canary_percent = 10, route 10% of prod traffic to GREEN
→ Monitor for 10 minutes:
  - Error rate
  - Latency (p50, p99)
  - Anomaly detection rate variance
→ If metrics stable, proceed to Step 5
→ If metrics degrade, automatic rollback (Step 6)
```

**Step 5: Traffic Switch**
```
→ Update load balancer target group:
  BLUE (old model): 0% traffic
  GREEN (new model): 100% traffic
→ Monitor for 5 minutes
→ If any alerts, trigger automatic rollback
```

**Step 6: Rollback** (on-demand or automatic)
```
→ If production metrics degrade:
  - Error rate spike > 2%
  - Latency p99 > 800ms
  - Anomaly false positive rate > 20%
→ BackupManager.restore_backup(last_version)
→ Update load balancer: reroute traffic back to BLUE
→ Log incident for post-mortem analysis
```

---

## 3. Model Registry Integration

The `ModelRegistry` class manages version tracking:

```python
# Register new trained model
registry = ModelRegistry()
registry.register_model(
    model_path="models/lstm_model.pkl",
    accuracy=0.9234,
    dataset_size=50000
)

# Query current deployment
latest = registry.get_latest_model()
# → {"version": 3, "name": "model_v3", "accuracy": 0.9234, ...}

# Rollback if needed
registry.rollback_to_version(2)
```

---

## 4. Canary Metrics

Monitor these KPIs during canary phase (10% traffic):

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | > 2.0% | Rollback |
| Latency p99 | > 800ms | Rollback |
| Anomaly Precision | < 0.85 | Rollback |
| OOM/Exceptions | > 10 in 10min | Rollback |

---

## 5. Automatic Rollback Triggers

The deployment pipeline automatically rolls back if:

1. **Health Check Failure**: GREEN pods fail to become Ready (120s timeout)
2. **Metric Degradation** (monitored via Prometheus alerts):
   - `ml_error_rate > 0.02` for > 2 minutes
   - `ml_latency_p99 > 800ms` for > 2 minutes
   - `ml_false_positives > 0.2` for > 5 minutes

---

## 6. Manual Rollback Procedure

**Admin endpoint** (requires JWT):

```bash
curl -X POST http://api.pulsetrakai.com/api/admin/rollback-model \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"version": 2}'
```

---

## 7. Post-Deployment Checklist

- [ ] Model version incremented in registry (v1 → v2)
- [ ] Backup created before deployment
- [ ] All health checks passed
- [ ] Prediction latency p99 < 500ms
- [ ] Error rate < 0.1%
- [ ] No memory leaks (RSS memory stable)
- [ ] Prometheus metrics increasing (successful predictions)
- [ ] Loki logs show no repeated errors
- [ ] Grafana dashboards show normal patterns
- [ ] Canary test successful (if enabled)
- [ ] Traffic switched to GREEN successfully
- [ ] No alerts triggered in first 5 minutes

---

## 8. Production Support

**If production issues occur**:

1. Check logs: `kubectl logs -f deployment/pulsetrakai-ml`
2. Check metrics: Prometheus dashboard "ML Model Performance"
3. Check Loki traces: `{job="ml-service"}`
4. Trigger rollback: `/api/admin/rollback-model`
5. Post-incident review in docs/incidents/

---

## 9. Model Versioning

Models follow semantic versioning in filenames:

- `model_v1.pkl` — First production model
- `model_v2.pkl` — Major feature change or retraining
- `model_v3.pkl` — Incremental improvement or bug fix

Registry automatically keeps last 3 versions; older models deleted.

---

## 10. Related Processes

- **Automated Retraining**: See [scheduler.py](../backend/ml/scheduler.py)
- **Backup Strategy**: See [docs/model-backup-policy.md](./model-backup-policy.md)
- **Cost Control**: See [docs/infra/cost-control.md](./infra/cost-control.md)
- **Release Governance**: See [docs/release-governance.md](./release-governance.md)
