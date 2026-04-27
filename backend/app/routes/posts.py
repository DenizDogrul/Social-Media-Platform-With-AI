from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, cast, Float, or_

from app.database import SessionLocal
from app.models.post import Post, TopicTag, PostTag, PostMedia
from app.models.follow import Follow
from app.models.like import Like
from app.models.bookmark import Bookmark
from app.schemas.post import PostCreate, PostUpdate
from app.services.ai_tags import generate_tags
from app.services.notifications import create_notification
from app.services.rate_limit import apply_rate_limit
from app.services.media_storage import get_media_storage, validate_upload
from app.auth import get_current_user
from app.models.user import User

from app.settings import FOLLOWED_FEED_RATIO

router = APIRouter(prefix="/posts", tags=["posts"])

MAX_MEDIA_BYTES = 30 * 1024 * 1024


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_post(post: Post, likes_count: int, is_liked: bool, is_bookmarked: bool = False) -> dict:
    media = post.media_items[0] if post.media_items else None
    return {
        "post_id": post.id,
        "title": post.title,
        "content": post.content,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "is_verified": bool(getattr(post.author, "is_verified", 0)),
        },
        "tags": [pt.tag.name for pt in post.tags if pt.tag],
        "likes": int(likes_count or 0),
        "is_liked": bool(is_liked),
        "is_bookmarked": bool(is_bookmarked),
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "media_url": media.media_url if media else None,
        "thumbnail_url": media.thumbnail_url if media else None,
        "media_type": media.media_type if media else None,
    }


@router.post("/upload-media", summary="Upload media file")
async def upload_media(
    request: Request,
    media: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit(request, bucket="posts_upload", limit=20, window_seconds=60, user_id=current_user.id)
    content_type = media.content_type or ""
    ext = ("." + (media.filename or "file.bin").split(".")[-1].lower()) if "." in (media.filename or "") else ""

    content = await media.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(content) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Media file is too large")

    try:
        validate_upload(content_type, ext, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    storage = get_media_storage()
    try:
        stored = storage.save(content=content, ext=ext, content_type=content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return {
        "media_url": stored.media_url,
        "thumbnail_url": stored.thumbnail_url,
        "media_type": stored.media_type,
        "uploaded_by": current_user.id,
    }


@router.post("/", summary="Create a new post")
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = Post(
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    if post_data.media_url and post_data.media_type:
        db.add(
            PostMedia(
                post_id=post.id,
                media_url=post_data.media_url,
                thumbnail_url=post_data.thumbnail_url,
                media_type=post_data.media_type,
            )
        )

    raw_tags = generate_tags(post_data.content)

    processed_tags = []
    seen = set()

    for tag in raw_tags:
        tag_clean = tag.lower().strip()
        if 1 <= len(tag_clean.split()) <= 3 and tag_clean not in seen:
            processed_tags.append(tag_clean)
            seen.add(tag_clean)

    created_tags = []

    for tag_name in processed_tags:
        tag = db.query(TopicTag).filter_by(name=tag_name).first()

        if not tag:
            tag = TopicTag(name=tag_name)
            db.add(tag)
            db.commit()
            db.refresh(tag)

        post_tag = PostTag(post_id=post.id, tag_id=tag.id)
        db.add(post_tag)
        created_tags.append(tag.name)

    db.commit()

    followers = db.query(Follow).filter(Follow.following_id == current_user.id).all()
    for follow in followers:
        await create_notification(
            db,
            user_id=follow.follower_id,
            event_type="new_post",
            title="New post from creator",
            body=f"@{current_user.username} shared a new post: {post.title}",
        )

    return {
        "post_id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "tags": created_tags,
        "media_url": post_data.media_url,
        "thumbnail_url": post_data.thumbnail_url,
        "media_type": post_data.media_type,
    }


@router.patch("/{post_id}", summary="Edit post")
def edit_post(
    post_id: int,
    payload: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).options(joinedload(Post.media_items)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    if payload.title is not None:
        post.title = payload.title
    if payload.content is not None:
        post.content = payload.content

    if payload.media_url is not None and payload.media_type is not None:
        db.query(PostMedia).filter(PostMedia.post_id == post.id).delete()
        db.add(
            PostMedia(
                post_id=post.id,
                media_url=payload.media_url,
                thumbnail_url=payload.thumbnail_url,
                media_type=payload.media_type,
            )
        )

    db.commit()
    db.refresh(post)
    return {"message": "Post updated"}


@router.delete("/{post_id}", summary="Delete post")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    db.query(PostTag).filter(PostTag.post_id == post_id).delete()
    db.query(PostMedia).filter(PostMedia.post_id == post_id).delete()
    db.query(Bookmark).filter(Bookmark.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"message": "Post deleted"}


@router.post("/{post_id}/like", summary="Like a post")
async def like_post(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apply_rate_limit(request, bucket="posts_like", limit=70, window_seconds=60, user_id=current_user.id)
    post = db.query(Post).options(joinedload(Post.author)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing_like = db.query(Like).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already liked this post")

    like = Like(user_id=current_user.id, post_id=post_id)
    db.add(like)
    db.commit()

    if post.author_id != current_user.id:
        await create_notification(
            db,
            user_id=post.author_id,
            event_type="post_liked",
            title="Your post got a like",
            body=f"@{current_user.username} liked your post: {post.title}",
        )
    return {"message": "Post liked successfully"}


@router.post("/{post_id}/unlike", summary="Unlike a post")
def unlike_post(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apply_rate_limit(request, bucket="posts_unlike", limit=70, window_seconds=60, user_id=current_user.id)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    like = db.query(Like).filter_by(user_id=current_user.id, post_id=post_id).first()
    if not like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have not liked this post")

    db.delete(like)
    db.commit()
    return {"message": "Post unliked successfully"}


@router.post("/{post_id}/bookmark", summary="Bookmark a post")
def bookmark_post(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apply_rate_limit(request, bucket="posts_bookmark", limit=70, window_seconds=60, user_id=current_user.id)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = db.query(Bookmark).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        return {"message": "Already bookmarked"}

    db.add(Bookmark(user_id=current_user.id, post_id=post_id))
    db.commit()
    return {"message": "Bookmarked"}


@router.delete("/{post_id}/bookmark", summary="Remove bookmark")
def unbookmark_post(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apply_rate_limit(request, bucket="posts_unbookmark", limit=70, window_seconds=60, user_id=current_user.id)
    item = db.query(Bookmark).filter_by(user_id=current_user.id, post_id=post_id).first()
    if not item:
        return {"message": "Not bookmarked"}
    db.delete(item)
    db.commit()
    return {"message": "Bookmark removed"}


@router.get("/{post_id}/likes", summary="Get users who liked a post")
def get_post_likes(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    likes = db.query(User).join(Like, Like.user_id == User.id).filter(Like.post_id == post_id).all()
    return [{"id": u.id, "username": u.username} for u in likes]


@router.get("/bookmarks/list", summary="Get bookmarked posts")
def list_bookmarks(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)

    rows = (
        db.query(Post, likes_count_expr.label("likes_count"), is_liked_expr.label("is_liked"))
        .join(Bookmark, Bookmark.post_id == Post.id)
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .filter(Bookmark.user_id == current_user.id)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [serialize_post(post, int(likes_count or 0), bool(is_liked), True) for post, likes_count, is_liked in rows]


def _feed_base_query(current_user: User, db: Session):
    likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
    bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
    is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)
    timestamp_factor = cast(func.strftime('%s', Post.created_at), Float) / 86400.0
    score_expr = (likes_count_expr * 2 + timestamp_factor).label("score")
    liked_exists_expr = liked_subq.c.liked_post_id.isnot(None)
    followed_exists_expr = Follow.id.isnot(None)

    query = (
        db.query(
            Post,
            likes_count_expr.label("likes_count"),
            is_liked_expr.label("is_liked"),
            is_bookmarked_expr.label("is_bookmarked"),
            score_expr,
        )
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
        .outerjoin(Follow, (Follow.following_id == Post.author_id) & (Follow.follower_id == current_user.id))
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
    )
    return query, followed_exists_expr, liked_exists_expr, score_expr


def _interleave_feed_rows(
    followed_rows: list,
    discover_rows: list,
    limit: int,
    followed_target: int,
    discover_target: int,
):
    items = []
    followed_idx = 0
    discover_idx = 0
    followed_used = 0
    discover_used = 0
    used_post_ids: set[int] = set()

    while len(items) < limit and (followed_idx < len(followed_rows) or discover_idx < len(discover_rows)):
        choose_followed = followed_used < followed_target
        if followed_used < followed_target and discover_used < discover_target:
            followed_progress = followed_used / max(followed_target, 1)
            discover_progress = discover_used / max(discover_target, 1)
            choose_followed = followed_progress <= discover_progress
        elif discover_used < discover_target:
            choose_followed = False

        source = followed_rows if choose_followed else discover_rows
        idx = followed_idx if choose_followed else discover_idx

        while idx < len(source):
            row = source[idx]
            post_id = row[0].id
            idx += 1
            if post_id in used_post_ids:
                continue

            used_post_ids.add(post_id)
            items.append(row)
            if choose_followed:
                followed_idx = idx
                followed_used += 1
            else:
                discover_idx = idx
                discover_used += 1
            break
        else:
            if choose_followed:
                followed_idx = idx
                followed_target = followed_used
            else:
                discover_idx = idx
                discover_target = discover_used

    return items


@router.get("/explore", summary="Discover trending posts")
def explore_posts(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
    bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()

    followed_authors_subq = db.query(Follow.following_id.label("followed_author_id")).filter(Follow.follower_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
    is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)
    novelty_bonus = case((followed_authors_subq.c.followed_author_id.is_(None), 1.4), else_=0.15)
    media_bonus = case((PostMedia.id.isnot(None), 0.35), else_=0.0)

    recency = cast(func.strftime('%s', Post.created_at), Float) / 86400.0
    explore_score = (likes_count_expr * 2.6 + recency + novelty_bonus + media_bonus).label("explore_score")

    rows = (
        db.query(
            Post,
            likes_count_expr.label("likes_count"),
            is_liked_expr.label("is_liked"),
            is_bookmarked_expr.label("is_bookmarked"),
            explore_score,
        )
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
        .outerjoin(followed_authors_subq, followed_authors_subq.c.followed_author_id == Post.author_id)
        .outerjoin(PostMedia, PostMedia.post_id == Post.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .order_by(explore_score.desc(), Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        serialize_post(post, int(likes_count or 0), bool(is_liked), bool(is_bookmarked))
        for post, likes_count, is_liked, is_bookmarked, _score in rows
    ]


@router.get("/feed", summary="Get personalized user feed with ranking")
def get_feed(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ratio = FOLLOWED_FEED_RATIO
    followed_limit = max(1, round(limit * ratio)) if limit > 1 else limit
    discover_limit = max(0, limit - followed_limit)

    followed_offset = int(offset * ratio)
    discover_offset = max(0, offset - followed_offset)

    base_query, followed_exists_expr, liked_exists_expr, score_expr = _feed_base_query(current_user, db)
    followed_query = base_query.filter(
        or_(
            followed_exists_expr,
            Post.author_id == current_user.id,
            liked_exists_expr,
        )
    )

    followed_rows = (
        followed_query
        .order_by(score_expr.desc(), Post.created_at.desc())
        .limit(max(followed_limit * 3, limit))
        .offset(followed_offset)
        .all()
    )

    discover_rows = []
    if discover_limit > 0:
        discover_query = base_query.filter(Post.author_id != current_user.id).filter(~followed_exists_expr)
        discover_rows = (
            discover_query
            .order_by(score_expr.desc(), Post.created_at.desc())
            .limit(max(discover_limit * 3, limit))
            .offset(discover_offset)
            .all()
        )

    query = _interleave_feed_rows(
        followed_rows=followed_rows,
        discover_rows=discover_rows,
        limit=limit,
        followed_target=followed_limit,
        discover_target=discover_limit,
    )

    # Fallback: if personalized feed is empty, show latest posts from all creators.
    if not query and offset == 0:
        likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
        liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
        bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()
        likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
        is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
        is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)

        query = (
            db.query(
                Post,
                likes_count_expr.label("likes_count"),
                is_liked_expr.label("is_liked"),
                is_bookmarked_expr.label("is_bookmarked"),
            )
            .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
            .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
            .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
            .options(
                joinedload(Post.author),
                joinedload(Post.tags).joinedload(PostTag.tag),
                joinedload(Post.media_items),
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    feed = []
    for row in query:
        post, likes_count, is_liked, is_bookmarked = row[0], row[1], row[2], row[3]
        feed.append(serialize_post(post, int(likes_count or 0), bool(is_liked), bool(is_bookmarked)))

    return feed


@router.get("/user/{user_id}", summary="Get posts by user")
def get_posts_by_user(
    user_id: int,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
    bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
    is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)

    rows = (
        db.query(
            Post,
            likes_count_expr.label("likes_count"),
            is_liked_expr.label("is_liked"),
            is_bookmarked_expr.label("is_bookmarked"),
        )
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        serialize_post(post, int(likes_count or 0), bool(is_liked), bool(is_bookmarked))
        for post, likes_count, is_liked, is_bookmarked in rows
    ]


@router.get("/tag/{tag_name}", summary="Get posts by tag")
def get_posts_by_tag(
    tag_name: str,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    likes_subq = db.query(Like.post_id, func.count(Like.id).label("likes_count")).group_by(Like.post_id).subquery()
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
    bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
    is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)

    normalized_tag = tag_name.strip().lower()

    rows = (
        db.query(
            Post,
            likes_count_expr.label("likes_count"),
            is_liked_expr.label("is_liked"),
            is_bookmarked_expr.label("is_bookmarked"),
        )
        .join(PostTag, PostTag.post_id == Post.id)
        .join(TopicTag, TopicTag.id == PostTag.tag_id)
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .filter(func.lower(TopicTag.name) == normalized_tag)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        serialize_post(post, int(likes_count or 0), bool(is_liked), bool(is_bookmarked))
        for post, likes_count, is_liked, is_bookmarked in rows
    ]


@router.get("/{post_id}", summary="Get post detail")
def get_post_detail(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    likes_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar() or 0
    is_liked = db.query(Like).filter_by(post_id=post_id, user_id=current_user.id).first() is not None
    is_bookmarked = db.query(Bookmark).filter_by(post_id=post_id, user_id=current_user.id).first() is not None

    return serialize_post(post, int(likes_count), bool(is_liked), bool(is_bookmarked))


@router.post("/{post_id}/repost", summary="Repost a post")
async def repost_post(
    post_id: int,
    request: Request,
    body: dict | None = None,  # Optional RepostCreate body for quote repost
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.repost import Repost

    # Parse JSON body if provided
    comment = None
    if body:
        comment = body.get("comment")
    else:
        try:
            body_data = await request.json()
            comment = body_data.get("comment") if body_data else None
        except:
            pass

    apply_rate_limit(request, bucket="posts_repost", limit=30, window_seconds=60, user_id=current_user.id)
    
    post = db.query(Post).options(joinedload(Post.author)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing_repost = db.query(Repost).filter_by(post_id=post_id, author_id=current_user.id).first()
    if existing_repost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already reposted this post")

    repost = Repost(
        post_id=post_id,
        original_post_id=post_id,
        author_id=current_user.id,
        comment=comment,
    )
    db.add(repost)
    db.commit()

    if post.author_id != current_user.id:
        await create_notification(
            db,
            user_id=post.author_id,
            event_type="post_reposted",
            title="Your post was reposted",
            body=f"@{current_user.username} reposted your post: {post.title}",
        )
    return {"message": "Post reposted successfully"}


@router.delete("/{post_id}/repost", summary="Remove repost")
def unrepost_post(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.repost import Repost
    apply_rate_limit(request, bucket="posts_unrepost", limit=30, window_seconds=60, user_id=current_user.id)
    
    repost = db.query(Repost).filter_by(post_id=post_id, author_id=current_user.id).first()
    if not repost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have not reposted this post")

    db.delete(repost)
    db.commit()
    return {"message": "Repost removed"}
