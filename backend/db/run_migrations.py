"""
Run SQL migration files against Postgres when `DATABASE_URL` is provided.

© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
"""
import os
import glob
import psycopg2


def run_migrations(database_url: str = None, migrations_dir: str = None):
    database_url = database_url or os.environ.get('DATABASE_URL')
    migrations_dir = migrations_dir or os.path.join(os.path.dirname(__file__), 'migrations')
    if not database_url:
        raise RuntimeError('DATABASE_URL not provided')

    sql_files = sorted(glob.glob(os.path.join(migrations_dir, '*.sql')))
    if not sql_files:
        return

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()
    for f in sql_files:
        with open(f, 'r', encoding='utf-8') as fh:
            sql = fh.read()
            try:
                cur.execute(sql)
            except Exception as e:
                # For idempotent migrations, ignore errors for already-existing objects
                print(f'Warning: migration {f} may have partially failed: {e}')
    cur.close()
    conn.close()


if __name__ == '__main__':
    run_migrations()
