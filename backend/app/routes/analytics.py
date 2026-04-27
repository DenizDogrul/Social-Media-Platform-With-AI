from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, cast, Float
from datetime import datetime, timedelta, UTC

from app.database import SessionLocal
from app.models.user import User
from app.models.post import Post, PostMedia, PostTag, TopicTag
from app.models.like import Like
from app.models.follow import Follow
from app.models.bookmark import Bookmark
from app.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary", summary="Get overall platform analytics (admin/debug)")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns basic platform metrics.
    Note: In production, this should be restricted to admin users.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_posts = db.query(func.count(Post.id)).scalar() or 0
    total_likes = db.query(func.count(Like.id)).scalar() or 0
    total_follows = db.query(func.count(Follow.id)).scalar() or 0

    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    active_last_24h = (
        db.query(func.count(func.distinct(Post.author_id)))
        .filter(Post.created_at >= last_24h)
        .scalar()
        or 0
    )

    posts_last_24h = (
        db.query(func.count(Post.id)).filter(Post.created_at >= last_24h).scalar() or 0
    )

    likes_last_24h = (
        db.query(func.count(Like.id)).filter(Like.created_at >= last_24h).scalar() or 0
    )

    avg_likes_per_post = (
        round(total_likes / max(total_posts, 1), 2) if total_posts > 0 else 0
    )
    engagement_rate = (
        round((total_likes / (total_posts * total_users)) * 100, 2)
        if total_posts > 0 and total_users > 0
        else 0
    )

    return {
        "timestamp": now.isoformat(),
        "platform": {
            "total_users": int(total_users),
            "total_posts": int(total_posts),
            "total_likes": int(total_likes),
            "total_follows": int(total_follows),
        },
        "last_24h": {
            "active_users": int(active_last_24h),
            "new_posts": int(posts_last_24h),
            "new_likes": int(likes_last_24h),
        },
        "metrics": {
            "avg_likes_per_post": avg_likes_per_post,
            "engagement_rate_pct": engagement_rate,
        },
    }


@router.get("/feed-distribution", summary="Get feed mix ratio compliance metrics")
def get_feed_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze feed distribution for current user:
    - How many posts from followed users vs discovered users are visible?
    - Validate fair-mix ratio compliance.
    """
    from app.settings import FOLLOWED_FEED_RATIO

    total_posts = db.query(func.count(Post.id)).scalar() or 0
    if total_posts == 0:
        return {
            "current_user_id": current_user.id,
            "target_followed_ratio": FOLLOWED_FEED_RATIO,
            "note": "No posts in system yet.",
        }

    followed_ids = (
        db.query(Follow.following_id)
        .filter(Follow.follower_id == current_user.id)
        .subquery()
    )

    followed_posts = (
        db.query(func.count(Post.id))
        .filter(Post.author_id.in_(followed_ids))
        .scalar()
        or 0
    )
    discover_posts = total_posts - followed_posts
    current_ratio = (
        round(followed_posts / max(total_posts, 1), 2)
        if total_posts > 0
        else 0
    )
    target_ratio = round(FOLLOWED_FEED_RATIO, 2)
    ratio_variance = round(abs(current_ratio - target_ratio), 2)

    return {
        "current_user_id": current_user.id,
        "feed_metrics": {
            "total_posts": int(total_posts),
            "followed_author_posts": int(followed_posts),
            "discover_posts": int(discover_posts),
        },
        "feed_ratio": {
            "target": target_ratio,
            "current": current_ratio,
            "variance": ratio_variance,
            "compliant": ratio_variance <= 0.1,
        },
    }


@router.get("/trending-posts", summary="Get most-engaged posts in last 7 days")
def get_trending_posts(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get trending/viral posts using recent likes and recency weighting."""

    last_7d = datetime.now(UTC) - timedelta(days=7)

    likes_subq = (
        db.query(Like.post_id, func.count(Like.id).label("likes_count"))
        .filter(Like.created_at >= last_7d)
        .group_by(Like.post_id)
        .subquery()
    )
    liked_subq = db.query(Like.post_id.label("liked_post_id")).filter(Like.user_id == current_user.id).subquery()
    bookmarked_subq = db.query(Bookmark.post_id.label("bookmarked_post_id")).filter(Bookmark.user_id == current_user.id).subquery()

    likes_count_expr = func.coalesce(likes_subq.c.likes_count, 0)
    is_liked_expr = case((liked_subq.c.liked_post_id.isnot(None), True), else_=False)
    is_bookmarked_expr = case((bookmarked_subq.c.bookmarked_post_id.isnot(None), True), else_=False)
    recency_bonus = cast(func.strftime('%s', Post.created_at), Float) / 86400.0
    media_bonus = case((PostMedia.id.isnot(None), 1.4), else_=0.0)
    trending_score = (likes_count_expr * 3.0 + recency_bonus + media_bonus).label("trending_score")

    rows = (
        db.query(
            Post,
            likes_count_expr.label("likes_count"),
            is_liked_expr.label("is_liked"),
            is_bookmarked_expr.label("is_bookmarked"),
            trending_score,
        )
        .join(User, Post.author_id == User.id)
        .outerjoin(likes_subq, likes_subq.c.post_id == Post.id)
        .outerjoin(liked_subq, liked_subq.c.liked_post_id == Post.id)
        .outerjoin(bookmarked_subq, bookmarked_subq.c.bookmarked_post_id == Post.id)
        .outerjoin(PostMedia, PostMedia.post_id == Post.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.media_items),
        )
        .filter(Post.created_at >= last_7d)
        .order_by(trending_score.desc(), Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    from app.routes.posts import serialize_post

    return [
        serialize_post(post, int(likes_count or 0), bool(is_liked), bool(is_bookmarked))
        for post, likes_count, is_liked, is_bookmarked, _score in rows
    ]


@router.get("/trending-tags", summary="Get trending tags in last 7 days")
def get_trending_tags(
    limit: int = 8,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    last_7d = datetime.now(UTC) - timedelta(days=7)
    like_counts = (
        db.query(Like.post_id, func.count(Like.id).label("likes_count"))
        .filter(Like.created_at >= last_7d)
        .group_by(Like.post_id)
        .subquery()
    )

    rows = (
        db.query(
            TopicTag.name,
            func.count(PostTag.id).label("post_count"),
            func.coalesce(func.sum(like_counts.c.likes_count), 0).label("likes_count"),
        )
        .join(PostTag, PostTag.tag_id == TopicTag.id)
        .join(Post, Post.id == PostTag.post_id)
        .outerjoin(like_counts, like_counts.c.post_id == Post.id)
        .filter(Post.created_at >= last_7d)
        .group_by(TopicTag.id, TopicTag.name)
        .order_by((func.count(PostTag.id) + func.coalesce(func.sum(like_counts.c.likes_count), 0)).desc(), TopicTag.name.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "tag": name,
            "post_count": int(post_count or 0),
            "likes_count": int(likes_count or 0),
            "score": int((post_count or 0) + (likes_count or 0)),
        }
        for name, post_count, likes_count in rows
    ]
