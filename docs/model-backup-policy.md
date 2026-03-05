# Model Backup & Recovery Policy — PulseTrakAI™

## Overview

This document defines the backup, archival, and disaster recovery procedures for ML model files. Protects against data loss, model corruption, and accidental deletions.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

---

## 1. Backup Strategy

### 1.1 Automatic Backups

**When**: Every model deployment to production
**How**: BackupManager creates a copy before replacing old model
**Where**: `/backups/model_backup_YYYYMMDD_HHMMSS.pkl`
**Retention**: 30 days (rolling window)

```python
from backend.ml.backup_manager import BackupManager

manager = BackupManager(
    backup_dir="backups",
    retention_days=30
)

# Automatically called before deploy:
backup = manager.create_backup(
    model_path="models/model_v2.pkl",
    reason="pre_deployment"
)
# → {"filename": "model_backup_20240115_143022.pkl", ...}
```

---

### 1.2 Manual Backups

Engineers can manually backup at any time:

```bash
# CLI command with admin auth
python -c "
from backend.ml.backup_manager import BackupManager
mgr = BackupManager()
mgr.create_backup('models/model_v2.pkl', reason='pre_testing')
"
```

**Use cases**:
- Before major version upgrades
- Before experimenting with training hyperparameters
- Before applying critical patches
- Before schema migrations

---

## 2. Backup Storage

### 2.1 Local Storage (Development)

```
backups/
├── model_backup_20240115_143022.pkl  (v1)
├── model_backup_20240110_120000.pkl  (v2)
├── model_backup_20240105_093500.pkl  (v3)
└── backup_manifest.json              (metadata)
```

**Size per backup**: ~5-50 MB (LSTM model)
**Total storage**: 30 days × ~20 MB/day = ~600 MB

---

### 2.2 Cloud Storage (Production)

**Primary**: S3 bucket `pulsetrakai-ml-backups`

```yaml
Bucket: pulsetrakai-ml-backups
Region: us-east-1
Versioning: Enabled
Lifecycle Rules:
  - Standard: 0-30 days (when current)
  - Glacier: 30-90 days (archived)
  - Expiration: Delete after 90 days
```

**Cost**: ~$1/month for 30-day rolling backups

---

## 3. Backup Manifest

**File**: `backup_manifest.json`

```json
{
  "backups": [
    {
      "id": "20240115_143022",
      "filename": "model_backup_20240115_143022.pkl",
      "path": "s3://pulsetrakai-ml-backups/model_backup_20240115_143022.pkl",
      "original_path": "models/model_v2.pkl",
      "created_at": "2024-01-15T14:30:22Z",
      "reason": "pre_deployment",
      "size_bytes": 45234567,
      "checksum": "sha256:abc123...",
      "model_version": 2,
      "training_accuracy": 0.9234,
      "training_date": "2024-01-14T08:00:00Z"
    },
    ...
  ]
}
```

---

## 4. Restore Procedures

### 4.1 Standard Restore (Last Backup)

**Scenario**: Current model corrupted, need to restore latest backup

```bash
# Via Python API
from backend.ml.backup_manager import BackupManager

manager = BackupManager()
backup_id = manager.list_backups(limit=1)[0]['id']
manager.restore_backup(backup_id, restore_path="models/model_v2.pkl")

# Verify restore
ls -lah models/model_v2.pkl
```

**Time**: < 2 minutes

---

### 4.2 Point-in-Time Restore

**Scenario**: Need to restore from specific date (e.g., 7 days ago)

```bash
# List all backups
python -c "
from backend.ml.backup_manager import BackupManager
mgr = BackupManager()
for b in mgr.list_backups(limit=20):
    print(f'{b[\"filename\"]}: {b[\"created_at\"]}')"

# Output:
# model_backup_20240115_143022.pkl: 2024-01-15T14:30:22Z
# model_backup_20240108_090000.pkl: 2024-01-08T09:00:00Z
# ...

# Restore from 2024-01-08
manager.restore_backup('20240108_090000', 'models/model_restored.pkl')
```

---

### 4.3 Remote Restore (from S3)

**Scenario**: Local backups deleted, need to restore from S3 archive

```bash
# Download from S3
aws s3 cp \
  s3://pulsetrakai-ml-backups/model_backup_20240108_090000.pkl \
  ./models/model_restored.pkl

# Verify checksum
sha256sum models/model_restored.pkl
# Compare with backup_manifest.json checksum
```

---

## 5. Backup Validation

### 5.1 Backup Integrity Check

Run weekly to verify backups are valid:

```bash
# scheduled_task: Every Sunday 3 AM UTC
python -c "
import pickle
from pathlib import Path

for backup_file in Path('backups/').glob('*.pkl'):
    try:
        with open(backup_file, 'rb') as f:
            model = pickle.load(f)
        print(f'✓ {backup_file} valid')
    except Exception as e:
        print(f'✗ {backup_file} corrupted: {e}')
        # Alert on-call engineer
"
```

---

### 5.2 Checksum Verification

Each backup stores SHA256 checksum in manifest:

```bash
# After restore, verify integrity
sha256sum models/model_v2.pkl > checksum.txt
# Compare with backup_manifest.json entry
grep "checksum" backup_manifest.json | head -1
```

---

## 6. Disaster Recovery Scenarios

### Scenario A: Single Model File Corrupted

```
1. Detect: Error loading model in production
2. Alert: Automatic rollback triggered
3. Restore: Load latest backup into memory
4. Time: < 5 minutes downtime
5. Action: Investigate root cause
```

**Recovery**:
```python
from backend.ml.backup_manager import BackupManager
manager = BackupManager()
manager.restore_backup('20240115_143022', 'models/model_v2.pkl')
# Reload model in FastAPI app
```

---

### Scenario B: All Backups Deleted Accidentally

```
1. Detect: Backup manifest empty or files missing
2. Alert: CRITICAL - no recovery path
3. Response: Retrain model from scratch (4-6 hours)
4. Impact: Degraded anomaly detection until retraining complete
```

**Prevention**:
- S3 versioning enabled (restore old version of manifest)
- Immutable backup copies (S3 Object Lock on Glacier tier)
- 3x geographic redundancy (multi-region S3 replication)

---

### Scenario C: Production Database Lost

```
1. Detect: Cannot query metric_events table
2. Impact: Cannot run retraining pipeline
3. Solution: Restore from RDS snapshot (1-2 hours)
4. Fallback: Use old backup model (predictions still work)
```

This policy focuses on **model backups**, not database backups.
For RDS disaster recovery, see [RDS Backup Strategy](../security-model.md#backup-and-recovery).

---

## 7. Retention Policy

| Backup Type | Retention | Location | Cost |
|------------|-----------|----------|------|
| Current version (v2) | Indefinite | `models/` | Included |
| Previous version (v1) | 30 days | `models/` | Small |
| Old backups (v0, older) | 30 days | `backups/` | < $1/month |
| Archive (90+ days) | 90 days total | S3 Glacier | ~$0.50/month |

**Cleanup Schedule**: Automatic at 2 AM UTC daily via `cleanup_old_backups()`

---

## 8. Monitoring

### 8.1 Prometheus Metrics

Track backup health:

```yaml
ml_backup_count           # Total backups in manifest
ml_backup_size_bytes      # Size of latest backup
ml_backup_age_hours       # Hours since last backup created
ml_backup_restore_seconds # Time to restore (test weekly)
ml_backup_validate_errors # Count of corrupted backups detected
```

### 8.2 Alerts

```yaml
BackupMissing:
  condition: ml_backup_age_hours > 48
  severity: critical
  action: Page on-call engineer

BackupCorrupted:
  condition: ml_backup_validate_errors > 0
  severity: high
  action: SNS notification

LargeSizeIncrease:
  condition: ml_backup_size_bytes > 200000000  # 200 MB
  severity: warning
  action: SNS notification
```

---

## 9. Testing & Verification

### 9.1 Backup Test (Weekly)

**Every Sunday 1 AM UTC**:

```bash
# Test backup creation
python -c "
from backend.ml.backup_manager import BackupManager
mgr = BackupManager()
backup = mgr.create_backup('models/model_v2.pkl', reason='weekly_test')
print(f'✓ Backup test passed: {backup[\"filename\"]}')
"
```

### 9.2 Restore Test (Monthly)

**First of each month**:

```bash
# Test recovery procedure
python -c "
from backend.ml.backup_manager import BackupManager
mgr = BackupManager()

# Pick 2nd oldest backup
backups = sorted(mgr.list_backups(limit=10), key=lambda x: x['created_at'])
old_backup = backups[1]

# Restore to temp location
mgr.restore_backup(old_backup['id'], '/tmp/model_test.pkl')

# Verify it loads
import pickle
with open('/tmp/model_test.pkl', 'rb') as f:
    model = pickle.load(f)
print('✓ Restore test passed')
"
```

---

## 10. Backup Cleanup

### 10.1 Local Cleanup (Automatic)

```python
# Runs daily at 2 AM UTC via cron
from backend.ml.backup_manager import BackupManager

manager = BackupManager(retention_days=30)
deleted_ids = manager.cleanup_old_backups()
# → Removes backups older than 30 days from /backups/ and S3
```

### 10.2 Manual Cleanup (if needed)

```bash
# Delete old backups
python -c "
from backend.ml.backup_manager import BackupManager
mgr = BackupManager(retention_days=7)  # Shorter retention
deleted = mgr.cleanup_old_backups()
print(f'Deleted {len(deleted)} backups')
"
```

---

## 11. Compliance & Audit

### 11.1 Backup Audit Log

Every backup creation/restore logged to database:

```sql
SELECT * FROM audit_log 
WHERE action IN ('backup_created', 'backup_restored')
ORDER BY created_at DESC
LIMIT 100;
```

**Fields**:
- `timestamp`: When action occurred
- `action`: 'backup_created' | 'backup_restored'
- `backup_id`: Identifier of backup
- `reason`: Why backup was created
- `user_id`: Admin who triggered (if manual)
- `status`: 'success' | 'failed'

### 11.2 Compliance Checks

- ✅ All backups verified weekly (no corruption)
- ✅ Restore tested monthly (recovery process works)
- ✅ Retention policy enforced (30-day max)
- ✅ Audit logs maintained (immutable)
- ✅ No secrets in backups (models are code + data, no creds)

---

## 12. Related Documentation

- [ML Deployment Strategy](./ml-deployment-strategy.md)
- [Release Governance](./release-governance.md)
- [Cost Control](./infra/cost-control.md)
- [Security Model](./security-model.md)

---

**Owner**: ML Infrastructure Team
**Last Updated**: 2024
**Review Cadence**: Quarterly
**Emergency Contact**: @devops-lead (Slack)
