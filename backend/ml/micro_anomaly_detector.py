"""
micro_anomaly_detector.py
Detect micro-anomalies comparing incoming events to temporal baselines.

Improvements:
- dynamic Z-score thresholds adapting to baseline variance
- temporal persistence: anomaly must persist for N minutes

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from typing import Dict, Any
import os
import sqlite3
import numpy as np
import pandas as pd
import time

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'data.db'))


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def detect_micro_anomaly(value: float, baseline_row: Dict[str, Any], dynamic_factor: float = 1.25) -> Dict:
    """Return anomaly info using dynamic z-score thresholding."""
    expected = float(baseline_row.get('expected_value', 0.0))
    std = float(baseline_row.get('std_dev', 0.0))
    if std <= 0:
        # fallback to relative delta
        denom = max(1.0, abs(expected))
        z = abs((value - expected) / denom)
    else:
        z = abs((value - expected) / std)

    # adaptive threshold: baseline std scaled by factor
    threshold = max(dynamic_factor, 1.0 + (std / (abs(expected) + 1e-6)))
    is_anomaly = z > threshold
    magnitude = float(z)
    return {
        'is_anomaly': bool(is_anomaly),
        'z_score': float(z),
        'magnitude': float(magnitude),
        'expected': expected,
        'std_dev': std,
        'threshold': float(threshold),
    }


def detect_persistent_anomaly(metric: str, window_minutes: int = 5, required_fraction: float = 0.6) -> Dict:
    """Check recent events for persistence of anomalies within window_minutes.

    required_fraction: fraction of events in window that must be anomalous to mark persistent.
    """
    now = int(time.time())
    conn = _get_conn()
    cur = conn.cursor()
    cutoff = now - int(window_minutes * 60)
    cur.execute('SELECT metric, value, timestamp FROM metric_events WHERE metric=? AND timestamp >= ? ORDER BY timestamp ASC', (metric, cutoff))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return {'metric': metric, 'persistent': False, 'details': 'no recent events'}
    # fetch baseline per row and count anomalies
    from .baseline_model import get_baseline_for
    anomalous = 0
    total = 0
    details = []
    for r in rows:
        val = float(r[1])
        ts = int(r[2])
        baseline = get_baseline_for(metric, ts)
        info = detect_micro_anomaly(val, baseline)
        details.append({'ts': ts, 'value': val, 'is_anomaly': info['is_anomaly'], 'z': info['z_score']})
        total += 1
        if info['is_anomaly']:
            anomalous += 1
    fraction = anomalous / total if total > 0 else 0.0
    persistent = fraction >= required_fraction
    return {'metric': metric, 'persistent': persistent, 'fraction': fraction, 'count': anomalous, 'total': total, 'details': details}
