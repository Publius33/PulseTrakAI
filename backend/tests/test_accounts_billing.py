import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from app.main import app, get_conn

client = TestClient(app)


def test_accounts_and_billing():
    rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
    assert rtok.status_code == 200
    token = rtok.json().get('access_token')

    # create account
    r = client.post('/api/accounts', json={'name': 'Team A', 'plan_id': 'basic', 'seats': 2}, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    acct = r.json()
    assert acct['name'] == 'Team A'

    # report usage and generate invoice
    ru = client.post('/api/billing/usage', json={'account_id': acct['id'], 'seats_used': 3}, headers={'Authorization': f'Bearer {token}'})
    assert ru.status_code == 200
    inv = ru.json()
    assert 'id' in inv

    # verify invoice persisted
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT amount_cents FROM invoices WHERE id=?", (inv['id'],))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert isinstance(row[0], int)
