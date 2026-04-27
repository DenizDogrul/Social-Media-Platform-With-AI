from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal
from app.models.comment import Comment
from app.models.moderation import Report, UserBlock, UserMute
from app.models.post import Post
from app.models.user import User

router = APIRouter(prefix="/moderation", tags=["moderation"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ReportCreate(BaseModel):
    target_type: str
    target_id: int
    reason: str
    details: str = ""


@router.post("/report", status_code=201)
def create_report(payload: ReportCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target_type = payload.target_type.lower().strip()

    report = Report(
        reporter_id=current_user.id,
        reason=payload.reason.strip()[:120] or "unspecified",
        details=(payload.details or "").strip()[:2000],
    )

    if target_type == "user":
        target = db.query(User).filter(User.id == payload.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")
        report.target_user_id = target.id
    elif target_type == "post":
        target = db.query(Post).filter(Post.id == payload.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target post not found")
        report.target_post_id = target.id
    elif target_type == "comment":
        target = db.query(Comment).filter(Comment.id == payload.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target comment not found")
        report.target_comment_id = target.id
    else:
        raise HTTPException(status_code=400, detail="target_type must be user, post, or comment")

    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": report.id, "status": report.status}


@router.post("/block/{user_id}")
def block_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(UserBlock).filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if existing:
        return {"message": "Already blocked"}

    db.add(UserBlock(blocker_id=current_user.id, blocked_id=user_id))
    db.commit()
    return {"message": "Blocked"}


@router.delete("/block/{user_id}")
def unblock_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(UserBlock).filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if not item:
        return {"message": "Not blocked"}
    db.delete(item)
    db.commit()
    return {"message": "Unblocked"}


@router.get("/blocks")
def list_blocks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(User)
        .join(UserBlock, UserBlock.blocked_id == User.id)
        .filter(UserBlock.blocker_id == current_user.id)
        .all()
    )
    return [{"id": u.id, "username": u.username} for u in rows]


@router.post("/mute/{user_id}")
def mute_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot mute yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(UserMute).filter_by(muter_id=current_user.id, muted_id=user_id).first()
    if existing:
        return {"message": "Already muted"}

    db.add(UserMute(muter_id=current_user.id, muted_id=user_id))
    db.commit()
    return {"message": "Muted"}


@router.delete("/mute/{user_id}")
def unmute_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(UserMute).filter_by(muter_id=current_user.id, muted_id=user_id).first()
    if not item:
        return {"message": "Not muted"}
    db.delete(item)
    db.commit()
    return {"message": "Unmuted"}


@router.get("/mutes")
def list_mutes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(User)
        .join(UserMute, UserMute.muted_id == User.id)
        .filter(UserMute.muter_id == current_user.id)
        .all()
    )
    return [{"id": u.id, "username": u.username} for u in rows]
