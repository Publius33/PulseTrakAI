"""
failure_chain_predictor.py
Detect precursor events and cluster anomalies to predict failure chains.

Upgrades:
- use recent metric_events from DB
- score precursors and return structured result

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from typing import List, Dict, Any
import os
import sqlite3
import numpy as np
import statistics
import time

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'data.db'))


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _recent_values(metric: str, period_seconds: int = 600):
    now = int(time.time())
    cutoff = now - period_seconds
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('SELECT value, timestamp FROM metric_events WHERE metric=? AND timestamp >= ? ORDER BY timestamp ASC', (metric, cutoff))
    rows = cur.fetchall()
    conn.close()
    return [float(r[0]) for r in rows]


def detect_precursors(metrics: List[str] = None) -> List[Dict[str, Any]]:
    """Detect precursor signatures across metrics and score them.

    Returns list of {'type', 'metric', 'score', 'description'}.
    """
    if metrics is None:
        metrics = ['cpu', 'memory', 'io', 'errors', 'latency']
    results = []
    # cpu drift: consistent upward trend over last 10 minutes
    vals = _recent_values('cpu', 600)
    if len(vals) >= 4:
        slope = np.polyfit(range(len(vals)), vals, 1)[0]
        score = float(min(max((slope / (np.mean(vals) + 1e-6)) * 2.0, 0.0), 1.0))
        if score > 0.15:
            results.append({'type': 'cpu_drift', 'metric': 'cpu', 'score': score, 'description': 'sustained CPU increase detected'})

    # memory leak: variance low but monotonic increase
    vals = _recent_values('memory', 900)
    if len(vals) >= 4:
        if all(vals[i] <= vals[i+1] for i in range(len(vals)-1)):
            med = statistics.median(vals)
            score = float(min(0.2 + (vals[-1] - med) / (med + 1e-6), 1.0))
            if score > 0.1:
                results.append({'type': 'memory_leak', 'metric': 'memory', 'score': score, 'description': 'memory trending upward without release'})

    # error spike: compare last value to recent mean
    vals = _recent_values('errors', 300)
    if len(vals) >= 3:
        last = vals[-1]
        mean = float(np.mean(vals[:-1])) if len(vals) > 1 else 0.0
        if mean > 0 and last > mean * 3:
            score = float(min((last - mean) / (mean + 1e-6), 1.0))
            results.append({'type': 'error_spike', 'metric': 'errors', 'score': score, 'description': 'sudden error-rate spike'})

    # high latency cluster detection
    vals = _recent_values('latency', 600)
    if len(vals) >= 5:
        p95 = np.percentile(vals, 95)
        median = np.median(vals)
        if p95 > median * 3:
            score = float(min((p95 - median) / (median + 1e-6) / 10.0, 1.0))
            results.append({'type': 'latency_cluster', 'metric': 'latency', 'score': score, 'description': 'high tail latency cluster detected'})

    return results


def aggregate_failure_chain(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate precursor detections into a single failure-chain prediction.

    predictions: list of {'type','metric','score',...}
    returns: {'overall_score', 'top_precursors': [...]}.
    """
    if not predictions:
        return {'overall_score': 0.0, 'top_precursors': []}
    sorted_preds = sorted(predictions, key=lambda p: p.get('score', 0.0), reverse=True)
    overall = float(min(1.0, sum(p.get('score', 0.0) for p in sorted_preds[:5]) / 2.0))
    return {'overall_score': overall, 'top_precursors': sorted_preds[:5]}
