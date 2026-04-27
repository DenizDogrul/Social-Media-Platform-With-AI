from datetime import UTC, datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import SessionLocal
from app.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.moderation import UserBlock
from app.services.notifications import create_notification
from app.services.realtime import message_hub

router = APIRouter(prefix="/messages", tags=["messages"])
logger = logging.getLogger(__name__)


def _is_blocked_between(db: Session, user_a_id: int, user_b_id: int) -> bool:
    return (
        db.query(UserBlock)
        .filter(
            or_(
                and_(UserBlock.blocker_id == user_a_id, UserBlock.blocked_id == user_b_id),
                and_(UserBlock.blocker_id == user_b_id, UserBlock.blocked_id == user_a_id),
            )
        )
        .first()
        is not None
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MessageCreate(BaseModel):
    content: str

@router.post("/conversations/{other_user_id}", status_code=201)
def create_or_get_conversation(other_user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if other_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    if _is_blocked_between(db, current_user.id, other_user_id):
        raise HTTPException(status_code=403, detail="Messaging unavailable due to block settings")

    u1, u2 = sorted([current_user.id, other_user_id])
    conv = db.query(Conversation).filter(and_(Conversation.user1_id == u1, Conversation.user2_id == u2)).first()
    if conv:
        return {"id": conv.id, "user1_id": conv.user1_id, "user2_id": conv.user2_id}

    conv = Conversation(user1_id=u1, user2_id=u2)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "user1_id": conv.user1_id, "user2_id": conv.user2_id}

@router.get("/conversations")
def my_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Conversation).filter(
        or_(Conversation.user1_id == current_user.id, Conversation.user2_id == current_user.id)
    ).all()
    return [{"id": c.id, "user1_id": c.user1_id, "user2_id": c.user2_id, "created_at": c.created_at} for c in items]

@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def send_message(conversation_id: int, payload: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="Not allowed")

    recipient_id = conv.user2_id if current_user.id == conv.user1_id else conv.user1_id
    if _is_blocked_between(db, current_user.id, recipient_id):
        raise HTTPException(status_code=403, detail="Messaging unavailable due to block settings")

    m = Message(conversation_id=conversation_id, sender_id=current_user.id, content=payload.content)
    db.add(m)
    db.commit()
    db.refresh(m)

    try:
        await create_notification(
            db,
            user_id=recipient_id,
            event_type="new_message",
            title="New direct message",
            body=f"@{current_user.username}: {payload.content[:100]}",
        )
    except Exception:
        logger.exception(
            "Message notification delivery failed",
            extra={"sender_id": current_user.id, "recipient_id": recipient_id, "conversation_id": conversation_id},
        )

    try:
        await message_hub.send_to_user(recipient_id, {
            "type": "new_message",
            "message": {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "sender_id": m.sender_id,
                "content": m.content,
                "is_read": m.is_read,
                "read_at": None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            },
        })
    except Exception:
        logger.exception("Message WS broadcast failed")

    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "sender_id": m.sender_id,
        "content": m.content,
        "is_read": m.is_read,
        "read_at": m.read_at.isoformat() if m.read_at else None,
        "created_at": m.created_at,
    }

@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="Not allowed")

    now = datetime.now(UTC).replace(tzinfo=None)
    incoming = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .all()
    )
    for item in incoming:
        item.is_read = True
        item.read_at = now
    if incoming:
        db.commit()

    items = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "sender_id": m.sender_id,
            "content": m.content,
            "is_read": m.is_read,
            "read_at": m.read_at.isoformat() if m.read_at else None,
            "created_at": m.created_at,
        }
        for m in items
    ]


@router.post("/conversations/{conversation_id}/read")
def mark_conversation_read(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="Not allowed")

    now = datetime.now(UTC).replace(tzinfo=None)
    items = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .all()
    )
    for item in items:
        item.is_read = True
        item.read_at = now
    db.commit()
    return {"message": "ok", "updated": len(items)}


@router.get("/unread-count")
def unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = (
        db.query(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            or_(Conversation.user1_id == current_user.id, Conversation.user2_id == current_user.id),
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .count()
    )
    return {"unread_count": int(count)}