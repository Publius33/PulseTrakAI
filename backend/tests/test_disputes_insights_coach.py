import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from app.main import app, get_conn

client = TestClient(app)


def test_dispute_insights_coach():
    rtok = client.post('/api/admin/login', json={'username': 'admin', 'password': 'adminpass'})
    assert rtok.status_code == 200
    token = rtok.json().get('access_token')

    # create dispute
    evidence = {'events': [{'timestamp': 1, 'note': 'first'}, {'timestamp': 2, 'note': 'second'}], 'messages': [{'text': 'No issues here'}]}
    r = client.post('/api/disputes', json={'customer_id': 'cus_x', 'title': 'Test', 'evidence': evidence}, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    jr = r.json()
    assert 'id' in jr
    report_id = jr['id']

    # get dispute
    rg = client.get(f'/api/disputes/{report_id}', headers={'Authorization': f'Bearer {token}'})
    assert rg.status_code == 200
    jg = rg.json()
    assert jg['id'] == report_id

    # run insights
    ri = client.post('/api/insights', json={'account_id': 'acct1', 'data': {}}, headers={'Authorization': f'Bearer {token}'})
    assert ri.status_code == 200
    ji = ri.json()
    assert 'summary' in ji

    # coach templates
    rc = client.get('/api/coach/templates', headers={'Authorization': f'Bearer {token}'})
    assert rc.status_code == 200
    jc = rc.json()
    assert 'templates' in jc
