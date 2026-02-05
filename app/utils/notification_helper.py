"""
Helper to create in-app notifications for KYC and order status updates.
"""
from sqlalchemy.orm import Session
from app.models.notification import Notification
from uuid import UUID


def create_notification(
    db: Session,
    user_id: str,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> Notification:
    """
    Create a notification for a user. Commits the notification; caller may be inside a larger transaction.
    user_id: User.id (string UUID).
    type: e.g. "kyc", "order", "delivery".
    data: optional payload, e.g. {"kyc_status": "verified"} or {"order_id": "...", "order_number": "...", "status": "..."}.
    """
    try:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
    except (ValueError, TypeError):
        uid = user_id
    notif = Notification(
        user_id=uid,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
