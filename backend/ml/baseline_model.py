"""
baseline_model.py
Compute and persist temporal baselines (hour/day) from metric events.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
from typing import List, Dict
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'data.db'))


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def compute_hourly_baseline(events: List[Dict]) -> pd.DataFrame:
    """Aggregate events into hourly baselines with mean/std.

    events: list of { 'metric': str, 'value': float, 'timestamp': str/int }
    returns DataFrame with columns ['metric','hour_of_day','day_of_week','expected_value','std_dev']
    """
    if not events:
        import pandas as pd
        return pd.DataFrame(columns=['metric','hour_of_day','day_of_week','expected_value','std_dev'])
    df = pd.DataFrame(events)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    grouped = df.groupby(['metric', 'hour_of_day', 'day_of_week'])['value']
    baseline = grouped.agg(['mean', 'std']).reset_index()
    baseline = baseline.rename(columns={'mean': 'expected_value', 'std': 'std_dev'})
    baseline['std_dev'] = baseline['std_dev'].fillna(0.0)
    return baseline[['metric', 'hour_of_day', 'day_of_week', 'expected_value', 'std_dev']]


def update_baselines_from_db(window_days: int = 14):
    """Compute baselines from recent metric_events and persist to `temporal_baselines` table.

    window_days: how many days of history to consider when building baselines.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('SELECT metric, value, timestamp FROM metric_events WHERE timestamp >= ?', (int(pd.Timestamp.now().timestamp()) - window_days * 86400,))
    rows = cur.fetchall()
    events = [{'metric': r[0], 'value': r[1], 'timestamp': r[2]} for r in rows]
    df = compute_hourly_baseline(events)
    # upsert into temporal_baselines
    for _, row in df.iterrows():
        cur.execute('INSERT OR REPLACE INTO temporal_baselines (metric, hour_of_day, day_of_week, expected_value, std_dev) VALUES (?, ?, ?, ?, ?)',
                    (row['metric'], int(row['hour_of_day']), int(row['day_of_week']), float(row['expected_value']), float(row['std_dev'])))
    conn.commit()
    conn.close()


def get_baseline_for(metric: str, ts) -> Dict:
    """Return baseline row (expected_value, std_dev) for the metric at timestamp `ts` (seconds).
    If no baseline found, returns defaults.
    """
    import datetime
    if isinstance(ts, (int, float)):
        dt = pd.to_datetime(ts, unit='s')
    else:
        dt = pd.to_datetime(ts)
    hour = int(dt.hour)
    dow = int(dt.dayofweek)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('SELECT expected_value, std_dev FROM temporal_baselines WHERE metric=? AND hour_of_day=? AND day_of_week=?', (metric, hour, dow))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {'expected_value': 0.0, 'std_dev': 0.0}
    return {'expected_value': float(row[0]), 'std_dev': float(row[1])}

