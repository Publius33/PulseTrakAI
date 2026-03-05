# Stage 5 Validation Checklist — PulseTrakAI™

## Overview

This document provides a comprehensive checklist to validate that all Stage 5 components are functioning correctly before marking the release as complete.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

---

## ✅ Component 1: GitHub Actions Pipelines

### 1.1 CI/CD Pipeline (ci-build.yml)

```
Manual Test:
  1. Push a commit to dev branch
  2. Wait 2-3 minutes for CI to start
  3. Check: Python deps install successfully
  4. Check: pytest runs 9 tests and passes
  5. Check: linting (pylint, flake8) passes
  6. Check: Docker builds succeed (backend, ml, frontend)
  7. Check: Smoke tests pass
  8. Acceptance: Workflow shows ✅ All Checks Passed
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 1.2 Staging Deployment (deploy-staging.yml)

```
Manual Test:
  1. Create a branch off staging and push
  2. Create PR to staging
  3. Wait for CI to pass, then merge to staging
  4. Check: deploy-staging.yml workflow triggered
  5. Check: Docker image builds with tag staging-latest
  6. Check: Image pushes to ECR/Docker registry
  7. Check: Health check on /health returns 200
  8. Check: /api/pulse-horizon responds with mock data
  9. Acceptance: Workflow completes with ✅ success
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 1.3 Production Deployment (deploy-production.yml)

```
Manual Test:
  1. Tag a commit on main: git tag v2.0.0
  2. Push tag: git push origin v2.0.0
  3. Check: deploy-production.yml triggered (tag: v2.0.0)
  4. Check: Docker image tagged and pushed
  5. Check: Blue/Green validation starts
  6. Check: Health checks pass on GREEN pods
  7. Check: Traffic switching logic executes
  8. Acceptance: Workflow completes with ✅ success
  9. (Optional) Verify rollback: git tag v2.0.1-rollback
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 1.4 ML Retraining Pipeline (ml-retrain.yml)

```
Manual Test:
  1. Trigger manually: GitHub Actions UI → ml-retrain.yml → Run Workflow
  2. Check: training_pipeline.py loads metric data from DB
  3. Check: Feature extraction computes FFT/STFT
  4. Check: LSTM training completes (even if mock)
  5. Check: Model validation accuracy computed
  6. Check: Model artifact saved to /models/model_vX.pkl
  7. Check: Workflow logs show completion message
  8. Acceptance: Workflow ✅ success
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 1.5 Version Release Automation (version-release.yml)

```
Manual Test:
  1. Trigger manually: GitHub Actions UI → version-release.yml
  2. Check: Semantic version bumped (patch, minor, or major)
  3. Check: Changelog generated or updated
  4. Check: Git tag created (v*.*.*)
  5. Check: GitHub Release created with notes
  6. Check: Release marked as latest
  7. Acceptance: Workflow ✅ success, Release visible in GitHub
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 2: Model Registry & Versioning

### 2.1 Model Registration

```python
Manual Test:
  1. Run: python -c "
    from backend.ml.model_registry import ModelRegistry
    registry = ModelRegistry()
    
    # Register a model
    result = registry.register_model(
        model_path='models/model_v1.pkl',
        accuracy=0.9234,
        dataset_size=50000
    )
    print(result)
  "
  2. Check: Model registered with version number
  3. Check: Metadata file updated (model_metadata.json)
  4. Check: File exists at models/model_v1.pkl
  5. Acceptance: Output shows success message
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 2.2 Model Retrieval

```python
Manual Test:
  1. Run: python -c "
    from backend.ml.model_registry import ModelRegistry
    registry = ModelRegistry()
    latest = registry.get_latest_model()
    print(f'Latest: {latest[\"name\"]}, Accuracy: {latest[\"validation_accuracy\"]}')
  "
  2. Check: Latest model returned correctly
  3. Run: python -c "
    from backend.ml.model_registry import ModelRegistry
    registry = ModelRegistry()
    print(registry.list_models())
  "
  4. Check: All registered models listed
  5. Acceptance: Output shows all models
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 2.3 Rollback Support

```python
Manual Test:
  1. Register 3 models (v1, v2, v3)
  2. Run: registry.rollback_to_version(2)
  3. Check: Current version set to v2
  4. Run: latest = registry.get_latest_model()
  5. Check: Returns v2 as current
  6. Acceptance: Rollback works
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 3: Retraining Scheduler

### 3.1 Scheduler Initialization

```python
Manual Test:
  1. Run: python -c "
    from backend.ml.scheduler import RetrainingScheduler
    
    def dummy_train():
        return {'status': 'training_done'}
    
    scheduler = RetrainingScheduler(
        training_func=dummy_train,
        anomaly_threshold=0.15
    )
    scheduler.start_scheduler()
    print(scheduler.get_job_status())
  "
  2. Check: Scheduler started successfully
  3. Check: 2 jobs registered: weekly_retrain, anomaly_check
  4. Check: Next run times calculated
  5. Acceptance: Output shows job status with next_run times
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 3.2 Scheduled Jobs

```
Manual Test:
  1. Start scheduler in foreground
  2. Wait 10 seconds, check logs
  3. Check: "Retraining scheduler started" message
  4. Check: "Added job: Weekly Model Retraining" logged
  5. Check: "Added job: Anomaly-triggered Retraining Check" logged
  6. Acceptance: Both jobs scheduled
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 4: Backup Manager

### 4.1 Backup Creation

```python
Manual Test:
  1. Create dummy model file:
    touch models/test_model.pkl && echo "dummy" > models/test_model.pkl
  
  2. Run: python -c "
    from backend.ml.backup_manager import BackupManager
    mgr = BackupManager()
    backup = mgr.create_backup('models/test_model.pkl', reason='test_backup')
    print(backup)
  "
  3. Check: Backup created in /backups/model_backup_*.pkl
  4. Check: Backup manifest updated
  5. Check: Backup info includes timestamp, size, reason
  6. Acceptance: Backup file exists and readable
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 4.2 Backup Listing

```python
Manual Test:
  1. Run: python -c "
    from backend.ml.backup_manager import BackupManager
    mgr = BackupManager()
    backups = mgr.list_backups(limit=5)
    for b in backups:
        print(f'{b[\"filename\"]}: {b[\"created_at\"]}')
  "
  2. Check: Recent backups listed with timestamps
  3. Check: Sorted by date (newest first)
  4. Acceptance: Output shows backup list
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 4.3 Backup Restoration

```python
Manual Test:
  1. Create and backup a file (see 4.1)
  2. Delete original: rm models/test_model.pkl
  3. Run: python -c "
    from backend.ml.backup_manager import BackupManager
    mgr = BackupManager()
    backups = mgr.list_backups(limit=1)
    mgr.restore_backup(backups[0]['id'], 'models/test_model_restored.pkl')
  "
  4. Check: File restored to new location
  5. Check: File is readable and matches backup
  6. Acceptance: Restored file exists and content matches
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 5: Model Reload Endpoint (API)

### 5.1 Reload Model (POST /api/admin/reload-model)

```
Manual Test:
  1. Start backend: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
  2. Register 2 models in registry (v1 and v2)
  3. Run: curl -X POST http://localhost:8000/api/admin/reload-model \\
           -H "Content-Type: application/json" \\
           -d '{"version": 2}'
  4. Check: Response includes {"status": "success", ...}
  5. Check: Model version 2 loaded
  6. Acceptance: Endpoint responds correctly
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 5.2 Model Status Endpoint (GET /api/admin/model-status)

```
Manual Test:
  1. Run: curl http://localhost:8000/api/admin/model-status
  2. Check: JSON response with current_version, models list, total_versions
  3. Check: All registered models listed
  4. Acceptance: Endpoint returns registry state
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 5.3 Rollback Endpoint (POST /api/admin/rollback-model)

```
Manual Test:
  1. Create 3 models (v1, v2, v3)
  2. Run: curl -X POST http://localhost:8000/api/admin/rollback-model \\
           -H "Content-Type: application/json" \\
           -d '{"version": 1}'
  3. Check: Response includes {"status": "success", ...}
  4. Check: Current version set to v1
  5. Acceptance: Rollback endpoint works
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 6: Documentation

### 6.1 ML Deployment Strategy

```
Manual Test:
  1. Open: docs/ml-deployment-strategy.md
  2. Check: Covers Blue/Green strategy
  3. Check: Health check procedures documented
  4. Check: Rollback triggers listed
  5. Check: Canary deployment procedure included
  6. Check: Post-deployment checklist provided
  7. Acceptance: Document complete and clear
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 6.2 Release Governance

```
Manual Test:
  1. Open: docs/release-governance.md
  2. Check: Git workflow (dev → staging → main) explained
  3. Check: Approval gates documented (CI, ML, code review)
  4. Check: Release checklist provided
  5. Check: Version numbering (MAJOR.MINOR.PATCH) explained
  6. Check: Rollback decision tree included
  7. Acceptance: Document complete and clear
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 6.3 Cost Control Strategy

```
Manual Test:
  1. Open: docs/infra/cost-control.md
  2. Check: Budget targets ($3,600/month) documented
  3. Check: Autoscaling rules (CPU > 70%, etc.) defined
  4. Check: Replica limits (backend: 2-10, ML: 1-6) specified
  5. Check: Cost monitoring metrics listed
  6. Check: Cost optimization checklist provided
  7. Acceptance: Document complete and clear
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 6.4 Model Backup Policy

```
Manual Test:
  1. Open: docs/model-backup-policy.md
  2. Check: 30-day retention policy stated
  3. Check: Backup creation procedures documented
  4. Check: Restore procedures documented
  5. Check: Disaster recovery scenarios included
  6. Check: Monitoring and alerts defined
  7. Acceptance: Document complete and clear
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 7: No Secrets Committed

### 7.1 Secret Scan

```
Manual Test:
  1. Run: git log -p | grep -i "api_key\|password\|secret\|token"
  2. Check: No sensitive values found
  3. Run: git ls-files | grep -i "\.env\|secrets\|creds"
  4. Check: No .env files or secrets files committed
  5. Acceptance: No secrets detected
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 7.2 Environment Variables

```
Verification:
  1. Check: All credentials in .env.example (not .env)
  2. Check: .gitignore includes: .env, *.pkl, /backups, /models
  3. Check: README.md documents how to set ENV vars
  4. Acceptance: No credentials in version control
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 8: Integration Tests

### 8.1 Test Suite Passes

```
Manual Test:
  1. Run: pytest backend/tests/ -v
  2. Check: test_accounts_billing.py: ✓
  3. Check: test_analytics_engine.py: ✓
  4. Check: test_disputes_insights_coach.py: ✓
  5. Check: test_main.py: ✓
  6. Check: test_plans.py: ✓
  7. Check: test_subscription_*.py: ✓
  8. Check: Total passing: 9 tests
  9. Acceptance: All tests pass
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 8.2 Container Tests

```
Manual Test:
  1. Run: docker-compose build
  2. Check: backend image builds ✓
  3. Check: ml image builds ✓
  4. Check: frontend image builds ✓
  5. Run: docker-compose up -d
  6. Wait 10 seconds for containers to start
  7. Run: curl http://localhost:8000/health
  8. Check: Response: {"status": "healthy"}
  9. Acceptance: All containers start successfully
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 9: Performance Baselines

### 9.1 Prediction Latency

```
Manual Test:
  1. Start backend service
  2. Make 100 prediction requests to /api/pulse-horizon
  3. Measure response times
  4. Calculate percentiles:
     - p50 (median): < 100ms ✓
     - p99 (99th): < 500ms ✓
     - p100 (max): < 1000ms ✓
  5. Acceptance: Latency within SLOs
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 9.2 Model Training Duration

```
Manual Test:
  1. Run: python -c "
    from backend.ml.training_pipeline import TrainingPipeline
    import time
    
    pipeline = TrainingPipeline()
    start = time.time()
    result = pipeline.run_training_pipeline('cpu_usage')
    elapsed = time.time() - start
    print(f'Training took {elapsed:.1f} seconds')
  "
  2. Check: Training completes in < 5 minutes
  3. Check: Model accuracy ≥ 0.88
  4. Acceptance: Training within SLOs
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Component 10: Monitoring & Observability

### 10.1 Prometheus Metrics Exported

```
Manual Test:
  1. Run: curl http://localhost:8000/metrics
  2. Check: Response includes Prometheus metric format
  3. Check: Metrics for: ml_predictions_total, ml_latency_ms, ml_accuracy, etc.
  4. Check: Metrics have proper labels (model_version, etc.)
  5. Acceptance: Metrics exported correctly
```

**Validation Result**: [ ] Pass / [ ] Fail

---

### 10.2 Logs Structured

```
Manual Test:
  1. Run: docker-compose logs backend | head -20
  2. Check: Logs include timestamp, level (INFO/ERROR), message
  3. Check: Sample log: "[2024-01-15 14:30:22] INFO: Model loaded successfully"
  4. Check: Error logs include stack traces
  5. Acceptance: Logs are structured and useful
```

**Validation Result**: [ ] Pass / [ ] Fail

---

## ✅ Deployment Readiness Sign-off

**All Components Complete?**

```
   ✓ CI/CD Pipelines (1.1-1.5): [ ] Yes / [ ] No
   ✓ Model Registry (2.1-2.3): [ ] Yes / [ ] No
   ✓ Scheduler (3.1-3.2): [ ] Yes / [ ] No
   ✓ Backup Manager (4.1-4.3): [ ] Yes / [ ] No
   ✓ API Endpoints (5.1-5.3): [ ] Yes / [ ] No
   ✓ Documentation (6.1-6.4): [ ] Yes / [ ] No
   ✓ No Secrets (7.1-7.2): [ ] Yes / [ ] No
   ✓ Tests Passing (8.1-8.2): [ ] Yes / [ ] No
   ✓ Performance (9.1-9.2): [ ] Yes / [ ] No
   ✓ Monitoring (10.1-10.2): [ ] Yes / [ ] No
```

---

## Final Approval

**Approver 1 (Backend Lead)**:
- Name: _____________________
- Date: _____________________
- Signature: _________________

**Approver 2 (DevOps Lead)**:
- Name: _____________________
- Date: _____________________
- Signature: _________________

**Approver 3 (Release Manager)**:
- Name: _____________________
- Date: _____________________
- Signature: _________________

---

**Stage 5 Status**: 
- [ ] COMPLETE — All validations passed, ready for production
- [ ] PENDING — Some components need rework (list below)

**Notes/Issues Found**:

```
1. ___________________________
2. ___________________________
3. ___________________________
```

---

## Related Documents

- [ML Deployment Strategy](./ml-deployment-strategy.md)
- [Release Governance](./release-governance.md)
- [Model Backup Policy](./model-backup-policy.md)
- [Cost Control](./infra/cost-control.md)

---

**Created**: 2024-01-15
**Last Updated**: 2024-01-15
**Review Frequency**: After each major release
