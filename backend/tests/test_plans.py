import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_plans():
    rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
    assert rtok.status_code == 200
    token = rtok.json().get('access_token')

    r = client.get('/api/plans', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    j = r.json()
    assert 'plans' in j
    assert any(p['id'] == 'basic' for p in j['plans'])
