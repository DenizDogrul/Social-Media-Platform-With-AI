import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.post import Post
from app.models.like import Like


client = TestClient(app)


def _unique_user(prefix="u"):
    token = uuid.uuid4().hex[:8]
    return {
        "username": f"{prefix}_{token}",
        "email": f"{prefix}_{token}@test.com",
        "password": "123456",
    }


def _register_and_login(user_payload: dict) -> str:
    r = client.post("/auth/register", json=user_payload)
    assert r.status_code in (200, 201), r.text

    r = client.post("/auth/login", json={
        "username": user_payload["username"],
        "password": user_payload["password"],
    })
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token
    return token


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def _create_post_db(author_username: str, title: str, content: str, created_at: datetime | None = None) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == author_username).first()
        assert user is not None

        post_kwargs = {"title": title, "content": content}

        # farklı projelerde FK adı değişebiliyor
        if hasattr(Post, "user_id"):
            post_kwargs["user_id"] = user.id
        elif hasattr(Post, "author_id"):
            post_kwargs["author_id"] = user.id
        elif hasattr(Post, "owner_id"):
            post_kwargs["owner_id"] = user.id

        post = Post(**post_kwargs)

        # FK alanı yoksa ilişki üzerinden bağla
        if not any(k in post_kwargs for k in ("user_id", "author_id", "owner_id")):
            if hasattr(post, "user"):
                post.user = user
            elif hasattr(post, "author"):
                post.author = user
            elif hasattr(post, "owner"):
                post.owner = user
            else:
                raise AssertionError("Post modelinde user ilişkisi/FK alanı bulunamadı")

        if created_at is not None and hasattr(post, "created_at"):
            post.created_at = created_at

        db.add(post)
        db.commit()
        db.refresh(post)
        return post.id
    finally:
        db.close()


def _feed_get(token: str):
    r = client.get("/posts/feed", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    return data


def _find_post(feed: list, post_id: int):
    for p in feed:
        if p.get("post_id") == post_id or p.get("id") == post_id:
            return p
    return None


def test_like_endpoints_require_jwt():
    r1 = client.post("/posts/1/like")
    r2 = client.post("/posts/1/unlike")
    r3 = client.get("/posts/1/likes")
    r4 = client.get("/posts/feed")

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
    assert r4.status_code == 401


def test_like_duplicate_and_unlike_validation():
    u = _unique_user("likev")
    token = _register_and_login(u)

    post_id = _create_post_db(u["username"], "p1", "content")

    # first like -> success
    r1 = client.post(f"/posts/{post_id}/like", headers=_auth_header(token))
    assert r1.status_code in (200, 201), r1.text

    # duplicate like -> blocked
    r2 = client.post(f"/posts/{post_id}/like", headers=_auth_header(token))
    assert r2.status_code in (400, 409), r2.text

    # unlike -> success
    r3 = client.post(f"/posts/{post_id}/unlike", headers=_auth_header(token))
    assert r3.status_code in (200, 204), r3.text

    # unlike again -> blocked
    r4 = client.post(f"/posts/{post_id}/unlike", headers=_auth_header(token))
    assert r4.status_code in (400, 404), r4.text


def test_get_post_likes_returns_users():
    owner = _unique_user("owner")
    liker = _unique_user("liker")

    owner_token = _register_and_login(owner)
    liker_token = _register_and_login(liker)

    post_id = _create_post_db(owner["username"], "liked post", "hello")
    r_like = client.post(f"/posts/{post_id}/like", headers=_auth_header(liker_token))
    assert r_like.status_code in (200, 201), r_like.text

    r = client.get(f"/posts/{post_id}/likes", headers=_auth_header(owner_token))
    assert r.status_code == 200, r.text
    body = r.json()

    # supports either: list[...] OR {"users": list[...]}
    users = body.get("users", body) if isinstance(body, dict) else body
    assert isinstance(users, list)
    assert any(
        (u.get("username") == liker["username"]) or (u.get("id") is not None)
        for u in users
    )


def test_feed_contains_likes_is_liked_and_ranking():
    a = _unique_user("a")
    b = _unique_user("b")
    c = _unique_user("c")

    token_a = _register_and_login(a)
    token_b = _register_and_login(b)
    token_c = _register_and_login(c)

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=3)
    new_time = now - timedelta(hours=1)

    old_post_id = _create_post_db(a["username"], "old high likes", "x", created_at=old_time)
    new_post_id = _create_post_db(b["username"], "new low likes", "y", created_at=new_time)

    # old_post gets 2 likes; new_post gets 1 like
    assert client.post(f"/posts/{old_post_id}/like", headers=_auth_header(token_b)).status_code in (200, 201, 409)
    assert client.post(f"/posts/{old_post_id}/like", headers=_auth_header(token_c)).status_code in (200, 201, 409)
    assert client.post(f"/posts/{new_post_id}/like", headers=_auth_header(token_c)).status_code in (200, 201, 409)

    feed = _feed_get(token_b)

    p_old = _find_post(feed, old_post_id)
    p_new = _find_post(feed, new_post_id)

    assert p_old is not None, "old post not found in feed"
    assert p_new is not None, "new post not found in feed"

    # format checks
    for p in (p_old, p_new):
        assert ("post_id" in p) or ("id" in p)
        assert "title" in p
        assert "content" in p
        assert "author" in p and isinstance(p["author"], dict)
        assert "created_at" in p
        assert ("likes" in p) or ("like_count" in p)
        assert "is_liked" in p

    old_likes = p_old.get("likes", p_old.get("like_count"))
    new_likes = p_new.get("likes", p_new.get("like_count"))

    assert isinstance(old_likes, int)
    assert isinstance(new_likes, int)
    assert old_likes >= new_likes

    # token_b liked old_post
    assert p_old["is_liked"] is True


def test_feed_mixes_followed_and_discover_posts():
    viewer = _unique_user("mix_viewer")
    followed_author = _unique_user("mix_followed")
    discover_author = _unique_user("mix_discover")

    token_viewer = _register_and_login(viewer)
    _register_and_login(followed_author)
    _register_and_login(discover_author)

    db = SessionLocal()
    try:
        viewer_db = db.query(User).filter(User.username == viewer["username"]).first()
        followed_db = db.query(User).filter(User.username == followed_author["username"]).first()
        assert viewer_db is not None
        assert followed_db is not None

        # Use API behavior equivalent follow relation so feed can classify sources.
        from app.models.follow import Follow

        existing = (
            db.query(Follow)
            .filter(Follow.follower_id == viewer_db.id, Follow.following_id == followed_db.id)
            .first()
        )
        if not existing:
            db.add(Follow(follower_id=viewer_db.id, following_id=followed_db.id))
            db.commit()
    finally:
        db.close()

    followed_post_id = _create_post_db(followed_author["username"], "followed post", "from followed")
    discover_post_id = _create_post_db(discover_author["username"], "discover post", "from discover")

    feed = _feed_get(token_viewer)

    assert _find_post(feed, followed_post_id) is not None, "followed content missing from feed"
    assert _find_post(feed, discover_post_id) is not None, "discover content missing from feed"