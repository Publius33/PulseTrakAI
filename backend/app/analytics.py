import time
import math
import json
import os
import sqlite3
import logging
from typing import List, Dict, Any

logger = logging.getLogger("pulsetrak.analytics")


def get_conn():
    db_path = os.environ.get("DB_PATH") or str(os.path.join(os.path.dirname(__file__), '..', 'data.db'))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ingest_metric(name: str, value: float, ts: int = None):
    ts = ts or int(time.time())
    conn = get_conn()
    cur = conn.cursor()
    # store simple metrics in metrics table as event rows by appending to JSON
    cur.execute("INSERT OR REPLACE INTO metrics (event, count, last_ts) VALUES (?, ?, ?)", (name, 1, ts))
    conn.commit()
    conn.close()


def fetch_recent_values(name: str, limit: int = 100) -> List[float]:
    # For demo, read metrics.count as a single value repeatedly (simple mock)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT count FROM metrics WHERE event=?", (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return []
    # return a list where the latest value is row[0], earlier values are slightly varied
    base = row[0]
    return [float(base + math.sin(i) * 0.5) for i in range(max(1, limit))]


def detect_anomalies(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"anomalies": []}
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(var)
    anomalies = []
    for i, v in enumerate(values[-10:]):
        if std > 0 and (v - mean) > 3 * std:
            anomalies.append({"index": i, "value": v, "mean": mean, "std": std})
    return {"anomalies": anomalies, "mean": mean, "std": std}


def run_analysis_for_metric(name: str) -> Dict[str, Any]:
    values = fetch_recent_values(name, limit=200)
    result = detect_anomalies(values)
    # create alerts if anomalies found
    if result.get('anomalies'):
        conn = get_conn()
        cur = conn.cursor()
        # guard: ensure alerts table exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                metric TEXT,
                payload_json TEXT,
                created_ts INTEGER
            )
            """
        )
        import uuid
        aid = str(uuid.uuid4())
        ts = int(time.time())
        cur.execute("INSERT INTO alerts (id, metric, payload_json, created_ts) VALUES (?, ?, ?, ?)", (aid, name, json.dumps(result), ts))
        conn.commit()
        conn.close()
        result['alert_id'] = aid
    return result


def list_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    # guard: ensure alerts table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            metric TEXT,
            payload_json TEXT,
            created_ts INTEGER
        )
        """
    )
    cur.execute("SELECT id, metric, payload_json, created_ts FROM alerts ORDER BY created_ts DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({"id": r[0], "metric": r[1], "payload": json.loads(r[2] or '{}'), "created_ts": r[3]})
    return out
