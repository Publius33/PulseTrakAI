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


def test_price_creation_and_reuse():
    mock_price = MagicMock()
    mock_price.id = 'price_1'

    mock_sub = MagicMock()
    mock_sub.id = 'sub_1'
    mock_sub.status = 'active'

    with patch('app.main.stripe') as stripe_mod:
        stripe_mod.Price.create.return_value = mock_price
        stripe_mod.Subscription.create.return_value = mock_sub

        # ensure no existing price mapping (tests share DB file)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM prices WHERE price_cents=? AND currency=?", (500, 'usd'))
        conn.commit()
        conn.close()

        # get admin token
        rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
        assert rtok.status_code == 200
        token = rtok.json().get('access_token')

        # create subscription first time (should create price)
        r1 = client.post('/api/subscriptions', json={'customer_stripe_id': 'cus_x', 'price_cents': 500, 'currency': 'usd'}, headers={'Authorization': f'Bearer {token}'})
        assert r1.status_code == 200
        js1 = r1.json()
        assert js1['id'] == 'sub_1'

        # create subscription second time (should reuse price; Price.create called only once)
        r2 = client.post('/api/subscriptions', json={'customer_stripe_id': 'cus_x', 'price_cents': 500, 'currency': 'usd'}, headers={'Authorization': f'Bearer {token}'})
        assert r2.status_code == 200
        js2 = r2.json()
        assert js2['id'] == 'sub_1'

        assert stripe_mod.Price.create.call_count == 1

        # list subscriptions
        rl = client.get('/api/subscriptions', headers={'Authorization': f'Bearer {token}'})
        assert rl.status_code == 200
        lst = rl.json()
        assert isinstance(lst, list)

        # verify price persisted in DB
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT stripe_price_id FROM prices WHERE price_cents=? AND currency=?", (500, 'usd'))
        prow = cur.fetchone()
        conn.close()
        assert prow is not None
        assert prow[0] == 'price_1'
