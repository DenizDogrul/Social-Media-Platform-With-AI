from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.database import SessionLocal
from app.auth import get_current_user
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.comment_like import CommentLike
from app.services.notifications import create_notification
from app.services.rate_limit import apply_rate_limit

router = APIRouter(prefix="/comments", tags=["comments"])
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CommentCreate(BaseModel):
    content: str
    parent_id: int | None = None

@router.post("/posts/{post_id}", status_code=201)
async def create_comment(post_id: int, payload: CommentCreate, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    apply_rate_limit(request, bucket="comments_create", limit=45, window_seconds=60, user_id=current_user.id)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if payload.parent_id is not None:
        parent = db.query(Comment).filter(Comment.id == payload.parent_id, Comment.post_id == post_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    c = Comment(content=payload.content, user_id=current_user.id, post_id=post_id, parent_id=payload.parent_id)
    db.add(c)
    db.commit()
    db.refresh(c)

    if post.author_id != current_user.id:
        try:
            await create_notification(
                db,
                user_id=post.author_id,
                event_type="new_comment",
                title="New comment on your post",
                body=f"@{current_user.username} commented on your post.",
            )
        except Exception:
            logger.exception("Comment notification failed")

    return {
        "id": c.id,
        "content": c.content,
        "user_id": c.user_id,
        "author_username": current_user.username,
        "post_id": c.post_id,
        "parent_id": c.parent_id,
        "likes": 0,
        "is_liked": False,
        "created_at": c.created_at,
    }

@router.get("/posts/{post_id}")
def list_comments(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()
    result = []
    for c in comments:
        likes_count = db.query(func.count(CommentLike.id)).filter(CommentLike.comment_id == c.id).scalar() or 0
        is_liked = db.query(CommentLike).filter_by(user_id=current_user.id, comment_id=c.id).first() is not None
        result.append({
            "id": c.id,
            "content": c.content,
            "user_id": c.user_id,
            "author_username": c.user.username if c.user else f"user-{c.user_id}",
            "post_id": c.post_id,
            "parent_id": getattr(c, "parent_id", None),
            "likes": int(likes_count),
            "is_liked": bool(is_liked),
            "created_at": c.created_at,
        })
    return result

@router.delete("/{comment_id}")
def delete_comment(comment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if c.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    db.delete(c)
    db.commit()
    return {"message": "Comment deleted"}


@router.post("/{comment_id}/like", status_code=201)
def like_comment(comment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db.query(CommentLike).filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already liked this comment")
    db.add(CommentLike(user_id=current_user.id, comment_id=comment_id))
    db.commit()
    return {"message": "Comment liked"}


@router.delete("/{comment_id}/like")
def unlike_comment(comment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cl = db.query(CommentLike).filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Not liked")
    db.delete(cl)
    db.commit()
    return {"message": "Comment unliked"}