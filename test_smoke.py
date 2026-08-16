from fastapi.testclient import TestClient

from main import app


def test_health_smoke():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    body = r.json()
    assert body['success'] is True
