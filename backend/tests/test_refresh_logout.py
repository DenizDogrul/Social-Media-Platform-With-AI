from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _unique_user(prefix: str = "u"):
    tag = f"{prefix}_{uuid4().hex[:8]}"
    return {"username": tag, "email": f"{tag}@test.com", "password": "Test1234!"}

def _register(user: dict):
    r = client.post("/users/register", json=user)
    assert r.status_code in (200, 201), r.text

def _login_and_get_tokens(user: dict):
    r = client.post("/users/login", json={"username": user["username"], "password": user["password"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data and "refresh_token" in data, data
    return data

def test_refresh_rotates_token():
    user = _unique_user("refresh")
    _register(user)
    tokens = _login_and_get_tokens(user)

    r = client.post("/users/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text
    new_tokens = r.json()

    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert "access_token" in new_tokens

    r2 = client.post("/users/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401, r2.text

def test_logout_revokes_refresh_token():
    user = _unique_user("logout")
    _register(user)
    tokens = _login_and_get_tokens(user)

    r = client.post("/users/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text

    r2 = client.post("/users/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401, r2.text