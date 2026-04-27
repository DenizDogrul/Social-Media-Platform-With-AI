from sqlalchemy.orm import Session
import json
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.services.realtime import notification_hub
from app.settings import PUSH_NOTIFICATIONS_ENABLED, VAPID_PRIVATE_KEY, VAPID_SUBJECT

try:
    from pywebpush import WebPushException, webpush
except Exception:  # pragma: no cover
    WebPushException = Exception
    webpush = None


def _send_web_push(db: Session, user_id: int, title: str, body: str, url: str) -> None:
    if not PUSH_NOTIFICATIONS_ENABLED or webpush is None:
        return

    subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    vapid_claims = {"sub": VAPID_SUBJECT}

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps({
                    "title": title,
                    "body": body,
                    "url": url,
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
        except WebPushException:
            db.delete(subscription)
            db.commit()


async def create_notification(
    db: Session,
    user_id: int,
    event_type: str,
    title: str,
    body: str,
    url: str = "/profile",
) -> Notification:
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    await notification_hub.send_to_user(
        user_id,
        {
            "type": "notification",
            "notification": {
                "id": notification.id,
                "event_type": notification.event_type,
                "title": notification.title,
                "body": notification.body,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "url": url,
            },
        },
    )
    _send_web_push(db, user_id, title, body, url)
    return notification
