# Infrastructure Cost Control Strategy — PulseTrakAI™

## Overview

This document defines the approach to managing and controlling AWS infrastructure costs while maintaining SLO (Service Level Objective) targets. Primary cost drivers: EC2 compute, RDS database, and data transfer.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

---

## 1. Cost Targets & Budget

| Component | Monthly Budget | Target Utilization |
|-----------|----------------|-------------------|
| EC2 (compute) | $2,500 | 60-75% CPU |
| RDS (database) | $800 | 50-70% CPU, 60% connections |
| Data Transfer | $300 | < 500GB/month |
| **Total** | **$3,600** | — |

---

## 2. Compute Resource Limits

### 2.1 Backend Service Replicas

```yaml
Min Replicas: 2
Max Replicas: 10
Target CPU: 70%
Target Memory: 75%
Instance Type: t4g.medium (ARM-based, cost-efficient)
```

**Scaling Rules**:
- Scale up if CPU > 70% for > 3 minutes
- Scale down if CPU < 30% for > 10 minutes
- Add 1-2 replicas per scale action
- Never drop below 2 replicas (HA requirement)

### 2.2 ML Service Replicas

```yaml
Min Replicas: 1
Max Replicas: 6
Target CPU: 75%
Instance Type: t4g.large (ML models require more memory)
```

**Scaling Rules**:
- Scale up if CPU > 75% OR prediction queue > 1000 for > 2 minutes
- Scale down if CPU < 40% for > 15 minutes
- Batch predictions to reduce API calls

### 2.3 Frontend Service Replicas

```yaml
Min Replicas: 2
Max Replicas: 4
Target CPU: 60%
Instance Type: t4g.small (lightweight)
```

---

## 3. Autoscaling Configuration (Kubernetes HPA)

```yaml
# backend HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pulsetrakai-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 180
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60

---

# ml-service HPA (same pattern with higher CPU threshold)
```

---

## 4. Database Cost Control

### 4.1 RDS PostgreSQL Configuration

```yaml
Instance Class: db.t4g.small
Storage: 100GB SSD (gp3)
Multi-AZ: Yes (cost: 2x compute, essential for HA)
Backup Retention: 7 days
```

**Cost-saving strategies**:
- Use `db.t4g` (burstable, cheaper than fixed performance)
- Estimated cost: $200/month (compute) + $20/month (storage)
- Enable gp3 (vs gp2) for 20% storage cost savings

### 4.2 Connection Pooling

```yaml
# PgBouncer connection pooling (max 200 connections)
max_client_conn: 200
default_pool_size: 20
reserve_pool_size: 5
```

Benefits: Reuse connections, reduce overhead, stay under RDS connection limit.

### 4.3 Query Optimization

Monitor slow queries via CloudWatch Logs:
```yaml
log_min_duration_statement: 1000  # Log queries > 1s
```

Optimize:
- Add indexes on `metric_id`, `timestamp`, `is_anomaly`
- Partition `metric_events` by month
- Archive events > 90 days to S3

---

## 5. Network Cost Control

### 5.1 Data Transfer Limits

| Direction | Monthly Limit | Cost Driver |
|-----------|---------------|------------|
| Internet → AWS | Unlimited | Not charged |
| AWS → Internet | 500GB/month | ~$0.09/GB |
| EC2 → RDS | Unlimited | Not charged (same AZ) |
| EC2 → S3 | Unlimited | Not charged |

**Mitigation**:
- GZip API responses (reduce egress ~60%)
- Cache static assets on CloudFront
- Limit real-time dashboard updates (batch requests)

### 5.2 S3 Costs (ML Models & Backups)

```yaml
Bucket: pulsetrakai-ml-models
Lifecycle Rules:
  - Transition to Glacier: 90 days
  - Delete: 180 days

Estimated cost: $50/month (model storage + backups)
```

---

## 6. Cost Monitoring Dashboards

### 6.1 Prometheus Metrics

Define custom metrics for cost visibility:

```yaml
# Container resource metrics (built-in)
container_cpu_usage_seconds_total
container_memory_usage_bytes

# Generate alerts:
- Backend CPU utilization > 85% for 5 min      → scale-up alert
- ML service latency p99 > 1s                   → scale-up alert
- Database connections > 150 / 200              → tuning alert
- RDS storage > 80GB                            → archival alert
```

### 6.2 Cost Breakdown

Use AWS Cost Explorer to track:
- EC2 On-Demand: should stay < $2,500/month
- RDS: should stay < $800/month
- Data Transfer: should stay < $300/month

---

## 7. Alerting Rules

Create CloudWatch alarms for cost events:

```yaml
Alarms:
  - name: UnusualEC2Spend
    metric: AWS/Billing/EstimatedCharges
    statistic: Average
    period: 86400  # daily
    threshold: 100  # $100/day = $3000/month
    action: SNS notification

  - name: HighDatabaseConnections
    metric: RDS/DatabaseConnections
    threshold: 150
    action: page on-call engineer

  - name: LargeDataTransfer
    metric: EC2/NetworkOut
    threshold: 20GB (daily)  # warn if daily > 20GB
    action: SNS notification
```

---

## 8. Reserved Instances (RI) Strategy

For stable baseline load:

```yaml
Backend Services (2 min replicas):
  - Purchase 2x t4g.medium RIs (1-year)
  - Estimated savings: 30% ($1,800/year)

ML Services (1 min replica):
  - Purchase 1x t4g.large RI (1-year)
  - Estimated savings: 30% ($800/year)
```

---

## 9. Disaster Recovery & Cost

**RPO/RTO Targets**:
- RPO (Recovery Point Objective): 1 hour
- RTO (Recovery Time Objective): 15 minutes

**Cost impact**:
- Multi-AZ RDS: +$400/month (2x compute)
- Cross-region backup: +$100/month (S3 & data transfer)
- Total DR overhead: ~$500/month (14% of budget)

---

## 10. Cost Optimization Checklist

- [ ] EC2 instances use t4g (graviton) for 20% savings
- [ ] RDS uses db.t4g.small (burstable)
- [ ] CloudFront caches static assets
- [ ] API responses GZip-compressed
- [ ] RDS backups retained only 7 days
- [ ] Old metric data (>90 days) archived to S3
- [ ] Reserved instances purchased for baseline load
- [ ] Autoscaling policies configured and tested
- [ ] Budget alerts configured in AWS Billing
- [ ] Monthly cost review against $3,600 target

---

## 11. Scaling Scenario Example

**Scenario**: Traffic spike (2M metrics/day → 5M metrics/day)

| Step | Action | Cost Impact | Duration |
|------|--------|-------------|----------|
| 1 | Backend scales: 2→6 replicas | +$40/day | Auto (3 min) |
| 2 | ML service scales: 1→4 replicas | +$60/day | Auto (2 min) |
| 3 | RDS connection pool optimized | $0 | Manual |
| 4 | Data transfer increases 50% | +$15/day | Ongoing |
| **Total** | **Temporary daily increase** | **+$115/day** | **~2 hours** |
| 5 | After traffic drop, scale down | -$100/day | Auto (30 min) |

Total cost for spike absorption: ~$500 (4-5 hours)

---

## 12. References

- AWS Cost Explorer: https://console.aws.amazon.com/cost-management/home
- Kubernetes HPA docs: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- Reserved Instances pricing: https://aws.amazon.com/ec2/pricing/reserved-instances/

---

**Next Review**: Monthly on 1st of each month
**Owner**: Infrastructure team
**Last Updated**: 2024
