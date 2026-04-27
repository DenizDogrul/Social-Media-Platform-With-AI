from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.settings import PUSH_NOTIFICATIONS_ENABLED, VAPID_PUBLIC_KEY

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushKeys


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "event_type": n.event_type,
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.get("/push-config")
def push_config(current_user: User = Depends(get_current_user)):
    del current_user
    return {
        "enabled": PUSH_NOTIFICATIONS_ENABLED,
        "public_key": VAPID_PUBLIC_KEY if PUSH_NOTIFICATIONS_ENABLED else "",
    }


@router.post("/push-subscriptions")
def register_push_subscription(
    payload: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": "updated"}

    item = PushSubscription(
        user_id=current_user.id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": "created"}


@router.delete("/push-subscriptions")
def delete_push_subscription(
    endpoint: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == endpoint, PushSubscription.user_id == current_user.id)
        .first()
    )
    if not item:
        return {"message": "Not found"}
    db.delete(item)
    db.commit()
    return {"message": "ok"}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not item:
        return {"message": "Not found"}
    item.is_read = True
    db.commit()
    return {"message": "ok"}


@router.post("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read.is_(False)).all()
    for item in items:
        item.is_read = True
    db.commit()
    return {"message": "ok", "count": len(items)}
