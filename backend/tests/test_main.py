import os
import sys
from pathlib import Path

os.environ.setdefault('ADMIN_JWT_SECRET', 'testsecret')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')

# Ensure backend package is importable when tests run from repo root or backend dir
sys.path.append(str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_and_status():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["message"] == "ok"

    r = client.get("/api/status")
    assert r.status_code == 200
    j = r.json()
    assert "name" in j and j["name"] == "PulseTrakAI"


def test_analytics_and_metrics():
    # track an event
    r = client.post("/api/analytics/track", json={"event": "page_view"})
    assert r.status_code == 200
    j = r.json()
    assert j.get("event") == "page_view"

    # obtain admin JWT
    r = client.post("/api/admin/login", json={"password": "adminpass"})
    assert r.status_code == 200
    token = r.json().get("access_token")
    assert token

    # metrics require admin JWT in Authorization header
    r = client.get("/api/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    arr = r.json()
    assert any(m["event"] == "page_view" for m in arr)
