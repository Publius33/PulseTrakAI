import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app, get_conn

client = TestClient(app)


def test_cancel_subscription_and_webhook():
    # Prepare DB entry
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO subscriptions (id, customer_id, stripe_id, status, price_cents, created_ts) VALUES (?, ?, ?, ?, ?, ?)", ('sub_cancel', None, 'sub_cancel', 'active', 500, 123456))
    conn.commit()
    conn.close()

    mock_del = MagicMock()
    mock_del.id = 'sub_cancel'
    mock_del.status = 'canceled'

    with patch('app.main.stripe') as stripe_mod:
        stripe_mod.Subscription.delete.return_value = mock_del

        rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
        assert rtok.status_code == 200
        token = rtok.json().get('access_token')

        rc = client.post('/api/subscriptions/sub_cancel/cancel', headers={'Authorization': f'Bearer {token}'})
        assert rc.status_code == 200
        js = rc.json()
        assert js['status'] == 'canceled'

        # webhook: simulate subscription deleted event
        event = {
            'type': 'customer.subscription.deleted',
            'data': {'object': {'id': 'sub_cancel', 'status': 'canceled'}}
        }
        rw = client.post('/api/webhooks/stripe', json=event)
        assert rw.status_code == 200

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT status FROM subscriptions WHERE id=?", ('sub_cancel',))
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'canceled'
