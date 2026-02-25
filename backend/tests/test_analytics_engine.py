import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from app.main import app, get_conn

client = TestClient(app)


def test_ingest_and_alerts():
    # get admin token
    rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
    assert rtok.status_code == 200
    token = rtok.json().get('access_token')

    # ingest a few values
    for i in range(5):
        r = client.post('/api/ingest', json={'name': 'page_view', 'value': 100 + i}, headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200

    # run analysis
    ra = client.post('/api/analytics/run', json={'metric': 'page_view'}, headers={'Authorization': f'Bearer {token}'})
    assert ra.status_code == 200
    jr = ra.json()
    assert 'anomalies' in jr

    # list alerts (may be empty)
    al = client.get('/api/alerts', headers={'Authorization': f'Bearer {token}'})
    assert al.status_code == 200
    ja = al.json()
    assert 'alerts' in ja
