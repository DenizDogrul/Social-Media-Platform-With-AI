from fastapi.testclient import TestClient

from app.main import app
from app.services.rate_limit import limiter

client = TestClient(app)


def test_users_login_rate_limited_after_threshold():
    limiter._hits.clear()

    payload = {"username": "nonexistent_user", "password": "bad-pass"}

    # /users/login allows 10 requests per minute from same identity.
    for _ in range(10):
        response = client.post("/users/login", json=payload)
        assert response.status_code in (400, 404), response.text

    blocked = client.post("/users/login", json=payload)
    assert blocked.status_code == 429, blocked.text
