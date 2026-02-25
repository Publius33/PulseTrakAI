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


def test_create_customer_and_subscription(monkeypatch):
    # Mock stripe.Customer.create and stripe.Subscription.create
    mock_cust = MagicMock()
    mock_cust.id = 'cus_test_123'
    mock_cust.email = 'test@example.com'

    mock_sub = MagicMock()
    mock_sub.id = 'sub_test_abc'
    mock_sub.status = 'active'

    with patch('app.main.stripe') as stripe_mod:
        stripe_mod.Customer.create.return_value = mock_cust
        stripe_mod.Subscription.create.return_value = mock_sub

        # get admin token
        rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
        assert rtok.status_code == 200
        token = rtok.json().get('access_token')

        # create customer
        r = client.post('/api/customers', json={'email': 'test@example.com'}, headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        jc = r.json()
        assert jc['id'] == 'cus_test_123'

        # create subscription
        r2 = client.post('/api/subscriptions', json={'customer_stripe_id': 'cus_test_123', 'price_cents': 500}, headers={'Authorization': f'Bearer {token}'})
        assert r2.status_code == 200
        js = r2.json()
        assert js['id'] == 'sub_test_abc'

        # check DB entry exists
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, status, price_cents FROM subscriptions WHERE id=?", ('sub_test_abc',))
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'sub_test_abc'
