from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_current_user
from app.database import SessionLocal
from app.models.follow import Follow
from app.models.moderation import Report
from app.models.post import Post
from app.models.user import User
from app.settings import ADMIN_BOOTSTRAP_USER_IDS

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if bool(getattr(current_user, "is_admin", 0)) or current_user.id in ADMIN_BOOTSTRAP_USER_IDS:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


class ReportStatusUpdate(BaseModel):
    status: str


@router.get("/overview")
def admin_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    total_users = db.query(func.count(User.id)).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == 1).scalar() or 0
    total_posts = db.query(func.count(Post.id)).scalar() or 0
    open_reports = db.query(func.count(Report.id)).filter(Report.status == "open").scalar() or 0
    total_follows = db.query(func.count(Follow.id)).scalar() or 0

    latest_reports = (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "metrics": {
            "total_users": int(total_users),
            "verified_users": int(verified_users),
            "total_posts": int(total_posts),
            "open_reports": int(open_reports),
            "total_follows": int(total_follows),
        },
        "recent_reports": [
            {
                "id": item.id,
                "reason": item.reason,
                "details": item.details,
                "status": item.status,
                "reporter_id": item.reporter_id,
                "target_user_id": item.target_user_id,
                "target_post_id": item.target_post_id,
                "target_comment_id": item.target_comment_id,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in latest_reports
        ],
    }


@router.get("/users")
def admin_list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    users = db.query(User).order_by(User.id.desc()).limit(100).all()
    results = []
    for user in users:
        posts_count = db.query(func.count(Post.id)).filter(Post.author_id == user.id).scalar() or 0
        followers_count = db.query(func.count(Follow.id)).filter(Follow.following_id == user.id).scalar() or 0
        results.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_verified": bool(user.is_verified),
                "is_admin": bool(user.is_admin) or user.id in ADMIN_BOOTSTRAP_USER_IDS,
                "posts_count": int(posts_count),
                "followers_count": int(followers_count),
            }
        )
    return results


@router.post("/users/{user_id}/verify")
def admin_toggle_verify(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    target.is_verified = 0 if bool(target.is_verified) else 1
    db.commit()
    db.refresh(target)
    return {"id": target.id, "is_verified": bool(target.is_verified)}


@router.post("/reports/{report_id}/status")
def admin_update_report_status(
    report_id: int,
    payload: ReportStatusUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    next_status = payload.status.strip().lower()
    if next_status not in {"open", "reviewed", "resolved"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report status")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = next_status
    db.commit()
    return {"id": report.id, "status": report.status}