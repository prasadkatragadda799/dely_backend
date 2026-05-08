"""
Helper to create in-app notifications for KYC and order status updates.
"""
from __future__ import annotations

from typing import Optional
import logging

from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User
from app.config import settings
from uuid import UUID

logger = logging.getLogger(__name__)
_fcm_initialized = False


def _send_fcm_push(token: str, title: str, body: str, data: Optional[dict] = None) -> None:
    """Send a Firebase Cloud Messaging push notification to one token."""
    global _fcm_initialized
    if not token or not settings.FCM_SERVICE_ACCOUNT_PATH:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except Exception as exc:
        logger.warning("firebase-admin is not installed or failed to import: %s", exc)
        return

    try:
        if not _fcm_initialized:
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.FCM_SERVICE_ACCOUNT_PATH)
                firebase_admin.initialize_app(cred)
            _fcm_initialized = True
    except Exception as exc:
        logger.warning("Failed to initialize Firebase Admin SDK: %s", exc)
        return

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
    )
    messaging.send(message)


def create_notification(
    db: Session,
    user_id: str,
    type: str,
    title: str,
    message: str,
    data: Optional[dict] = None,
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

    # Push the same notification over FCM for real-time delivery to the mobile app.
    try:
        user = db.query(User).filter(User.id == str(uid)).first()
        if user and user.fcm_token:
            _send_fcm_push(
                token=user.fcm_token,
                title=title,
                body=message,
                data={
                    "type": type,
                    **(data or {}),
                },
            )
    except Exception as exc:
        logger.warning("Failed to send FCM notification to user %s: %s", user_id, exc)

    return notif
