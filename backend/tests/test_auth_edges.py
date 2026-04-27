from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token

client = TestClient(app)

def _u(prefix="edge"):
    tag = f"{prefix}_{uuid4().hex[:8]}"
    return {"username": tag, "email": f"{tag}@test.com", "password": "Test1234!"}

def test_register_duplicate_username_or_email():
    user = _u("dup")
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post("/users/register", json=user)
    assert r2.status_code == 400, r2.text

def test_login_wrong_password():
    user = _u("wrongpass")
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post("/users/login", json={"username": user["username"], "password": "BadPass123!"})
    assert r2.status_code == 400, r2.text

def test_refresh_rejects_access_token():
    user = _u("toktype")
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    access = create_access_token({"sub": user["username"], "type": "access"})
    r2 = client.post("/users/refresh", json={"refresh_token": access})
    assert r2.status_code == 401, r2.text