"""Simple migration helper for PulseTrakAI backend.

This script ensures required tables exist when upgrading from older versions.
Run: `python backend/migrate.py` or import and call `run()`.
"""
import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get('DB_PATH', str(Path(BASE_DIR) / 'data.db'))

SQL = [
    """
    CREATE TABLE IF NOT EXISTS prices (
        id TEXT PRIMARY KEY,
        price_cents INTEGER,
        currency TEXT,
        stripe_price_id TEXT,
        created_ts INTEGER
    )
    """,
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for s in SQL:
        cur.execute(s)
    conn.commit()
    conn.close()


if __name__ == '__main__':
    run()
    print('Migrations applied (prices table ensured).')
