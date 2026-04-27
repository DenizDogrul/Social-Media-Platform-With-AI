from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)


def _unique_user(prefix: str):
    seed = uuid4().hex[:8]
    return {
        "username": f"{prefix}_{seed}",
        "email": f"{prefix}_{seed}@example.com",
        "password": "Test1234!",
    }


def _register_and_login(user: dict) -> str:
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text
    r2 = client.post("/users/login", json={"username": user["username"], "password": user["password"]})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _user_id(username: str) -> int:
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.username == username).first()
        assert row is not None
        return row.id
    finally:
        db.close()


def test_block_prevents_follow_and_message_flow():
    a = _unique_user("blkA")
    b = _unique_user("blkB")
    token_a = _register_and_login(a)
    token_b = _register_and_login(b)
    b_id = _user_id(b["username"])

    r_block = client.post(f"/moderation/block/{b_id}", headers=_auth(token_a))
    assert r_block.status_code == 200, r_block.text

    r_follow = client.post(f"/users/{b_id}/follow", headers=_auth(token_a))
    assert r_follow.status_code == 403, r_follow.text

    r_conv = client.post(f"/messages/conversations/{b_id}", headers=_auth(token_a))
    assert r_conv.status_code == 403, r_conv.text

    # unblock and retry messaging
    r_unblock = client.delete(f"/moderation/block/{b_id}", headers=_auth(token_a))
    assert r_unblock.status_code == 200, r_unblock.text

    r_conv2 = client.post(f"/messages/conversations/{b_id}", headers=_auth(token_a))
    assert r_conv2.status_code == 201, r_conv2.text

    conv_id = r_conv2.json()["id"]
    r_send = client.post(
        f"/messages/conversations/{conv_id}/messages",
        json={"content": "hello"},
        headers=_auth(token_a),
    )
    assert r_send.status_code == 201, r_send.text

    r_unread = client.get("/messages/unread-count", headers=_auth(token_b))
    assert r_unread.status_code == 200, r_unread.text
    assert r_unread.json()["unread_count"] >= 1

    r_list = client.get(f"/messages/conversations/{conv_id}/messages", headers=_auth(token_b))
    assert r_list.status_code == 200, r_list.text
    body = r_list.json()
    assert any(m["is_read"] for m in body)
    assert any(m["read_at"] is not None for m in body if m["sender_id"] != b_id)

    r_unread_after = client.get("/messages/unread-count", headers=_auth(token_b))
    assert r_unread_after.status_code == 200, r_unread_after.text
    assert r_unread_after.json()["unread_count"] == 0


def test_report_and_mute_lifecycle():
    a = _unique_user("modA")
    b = _unique_user("modB")
    token_a = _register_and_login(a)
    _register_and_login(b)
    b_id = _user_id(b["username"])

    r_mute = client.post(f"/moderation/mute/{b_id}", headers=_auth(token_a))
    assert r_mute.status_code == 200, r_mute.text

    r_mutes = client.get("/moderation/mutes", headers=_auth(token_a))
    assert r_mutes.status_code == 200, r_mutes.text
    assert any(x["id"] == b_id for x in r_mutes.json())

    r_report = client.post(
        "/moderation/report",
        json={"target_type": "user", "target_id": b_id, "reason": "abuse", "details": "spam content"},
        headers=_auth(token_a),
    )
    assert r_report.status_code == 201, r_report.text

    r_unmute = client.delete(f"/moderation/mute/{b_id}", headers=_auth(token_a))
    assert r_unmute.status_code == 200, r_unmute.text
