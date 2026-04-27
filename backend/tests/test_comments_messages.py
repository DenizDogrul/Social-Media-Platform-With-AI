from uuid import uuid4
from datetime import datetime, UTC

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.post import Post

client = TestClient(app)


def _unique_user(prefix: str):
    tag = f"{prefix}_{uuid4().hex[:8]}"
    return {
        "username": tag,
        "email": f"{tag}@test.com",
        "password": "Test1234!",
    }


def _register_and_login(user: dict) -> str:
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post("/users/login", json={"username": user["username"], "password": user["password"]})
    assert r2.status_code == 200, r2.text
    data = r2.json()
    return data["access_token"]


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def _create_post_db(username: str, title: str, content: str) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None, "user not found for post creation"

        kwargs = {"title": title, "content": content}
        if hasattr(Post, "created_at"):
            kwargs["created_at"] = datetime.now(UTC).replace(tzinfo=None)

        # farklı model adlandırmalarına uyum
        if hasattr(Post, "user_id"):
            kwargs["user_id"] = user.id
        elif hasattr(Post, "author_id"):
            kwargs["author_id"] = user.id
        elif hasattr(Post, "owner_id"):
            kwargs["owner_id"] = user.id
        elif hasattr(Post, "user"):
            kwargs["user"] = user
        elif hasattr(Post, "author"):
            kwargs["author"] = user
        else:
            raise AssertionError("Post modelinde kullanıcı alanı bulunamadı")

        post = Post(**kwargs)
        db.add(post)
        db.commit()
        db.refresh(post)
        return post.id
    finally:
        db.close()


def test_comment_create_list_delete():
    u = _unique_user("cmt")
    token = _register_and_login(u)
    post_id = _create_post_db(u["username"], "post1", "hello")

    r1 = client.post(f"/comments/posts/{post_id}", json={"content": "ilk yorum"}, headers=_auth_header(token))
    assert r1.status_code == 201, r1.text
    comment = r1.json()
    cid = comment["id"]

    r2 = client.get(f"/comments/posts/{post_id}")
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert any(x["id"] == cid for x in items)

    r3 = client.delete(f"/comments/{cid}", headers=_auth_header(token))
    assert r3.status_code == 200, r3.text


def test_comment_delete_forbidden_for_other_user():
    owner = _unique_user("ownerc")
    other = _unique_user("otherc")

    owner_token = _register_and_login(owner)
    other_token = _register_and_login(other)

    post_id = _create_post_db(owner["username"], "post2", "world")
    r1 = client.post(f"/comments/posts/{post_id}", json={"content": "owner comment"}, headers=_auth_header(owner_token))
    assert r1.status_code == 201, r1.text
    cid = r1.json()["id"]

    r2 = client.delete(f"/comments/{cid}", headers=_auth_header(other_token))
    assert r2.status_code == 403, r2.text


def test_messages_conversation_send_and_list():
    a = _unique_user("msgA")
    b = _unique_user("msgB")

    token_a = _register_and_login(a)
    token_b = _register_and_login(b)

    # b kullanıcısının id'sini DB'den bul
    db = SessionLocal()
    try:
        user_b = db.query(User).filter(User.username == b["username"]).first()
        assert user_b is not None
        b_id = user_b.id
    finally:
        db.close()

    # konuşma aç / getir
    r1 = client.post(f"/messages/conversations/{b_id}", headers=_auth_header(token_a))
    assert r1.status_code == 201, r1.text
    conv_id = r1.json()["id"]

    # mesaj gönder
    r2 = client.post(
        f"/messages/conversations/{conv_id}/messages",
        json={"content": "selam"},
        headers=_auth_header(token_a),
    )
    assert r2.status_code == 201, r2.text

    r3 = client.get(f"/messages/conversations/{conv_id}/messages", headers=_auth_header(token_b))
    assert r3.status_code == 200, r3.text
    msgs = r3.json()
    assert len(msgs) >= 1
    assert any(m["content"] == "selam" for m in msgs)


def test_messages_cannot_message_yourself():
    u = _unique_user("selfmsg")
    token = _register_and_login(u)

    db = SessionLocal()
    try:
        me = db.query(User).filter(User.username == u["username"]).first()
        assert me is not None
        my_id = me.id
    finally:
        db.close()

    r = client.post(f"/messages/conversations/{my_id}", headers=_auth_header(token))
    assert r.status_code == 400, r.text