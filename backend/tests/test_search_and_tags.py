from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.post import Post, PostTag, TopicTag
from app.models.user import User

client = TestClient(app)


def _unique_user(prefix: str):
    token = uuid4().hex[:8]
    return {
        "username": f"{prefix}_{token}",
        "email": f"{prefix}_{token}@test.com",
        "password": "Test1234!",
    }


def _register_and_login(user: dict) -> str:
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post("/users/login", json={"username": user["username"], "password": user["password"]})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def _create_post_with_tag(username: str, title: str, content: str, tag_name: str) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None

        post = Post(title=title, content=content, author_id=user.id)
        db.add(post)
        db.commit()
        db.refresh(post)

        tag = db.query(TopicTag).filter(TopicTag.name == tag_name).first()
        if not tag:
            tag = TopicTag(name=tag_name)
            db.add(tag)
            db.commit()
            db.refresh(tag)

        db.add(PostTag(post_id=post.id, tag_id=tag.id))
        db.commit()

        return post.id
    finally:
        db.close()


def test_login_supports_email_identifier_case_insensitive():
    user = _unique_user("email_login")
    r1 = client.post("/users/register", json=user)
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post(
        "/users/login",
        json={"username": user["email"].upper(), "password": user["password"]},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_unified_search_returns_users_tags_and_posts():
    user = _unique_user("nebulauser")
    token = _register_and_login(user)
    _create_post_with_tag(
        username=user["username"],
        title="Nebula Search Post",
        content="content for unified search tests",
        tag_name="nebula-search",
    )

    r = client.get("/users/search", params={"q": "nebula"}, headers=_auth_header(token))
    assert r.status_code == 200, r.text
    body = r.json()

    assert "users" in body and isinstance(body["users"], list)
    assert "tags" in body and isinstance(body["tags"], list)
    assert "posts" in body and isinstance(body["posts"], list)

    assert any(u["username"] == user["username"] for u in body["users"])
    assert any(t["name"] == "nebula-search" for t in body["tags"])
    assert any("Nebula Search Post" in p["title"] for p in body["posts"])


def test_posts_by_tag_endpoint_returns_tagged_posts():
    user = _unique_user("tag")
    token = _register_and_login(user)
    post_id = _create_post_with_tag(
        username=user["username"],
        title="Tag Flow Post",
        content="tag endpoint content",
        tag_name="tag-flow",
    )

    r = client.get("/posts/tag/tag-flow", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    rows = r.json()
    assert isinstance(rows, list)
    assert any(row.get("post_id") == post_id for row in rows)
