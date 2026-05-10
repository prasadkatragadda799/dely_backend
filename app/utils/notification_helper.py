"""
Helper to create in-app notifications for KYC, order, payment, and delivery flows.

Notifications are dual-channel:
1. Persisted to the `notifications` DB table (user inbox).
2. Pushed via Firebase Cloud Messaging (FCM) to the device token if registered.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.delivery_person import DeliveryPerson
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)
_fcm_initialized = False


def _resolve_service_account_path() -> Optional[str]:
    """
    Resolve the FCM service account JSON path. Priority order:
    1. settings.FCM_SERVICE_ACCOUNT_PATH env var (if file exists).
    2. Auto-discovered Firebase Admin SDK JSON file in the project root
       (matches `*-firebase-adminsdk-*.json`).
    """
    configured = (settings.FCM_SERVICE_ACCOUNT_PATH or "").strip()
    if configured and os.path.isfile(configured):
        return configured

    # Walk up from this file to find the project root, then look for the SDK file.
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "app").is_dir() and (parent / "requirements.txt").is_file():
            for candidate in parent.glob("*firebase-adminsdk*.json"):
                if candidate.is_file():
                    return str(candidate)
            break
    return None


def _ensure_fcm_initialized() -> bool:
    """Initialize Firebase Admin SDK once. Returns True if usable."""
    global _fcm_initialized

    if _fcm_initialized:
        return True

    sa_path = _resolve_service_account_path()
    if not sa_path:
        logger.warning(
            "FCM disabled: no Firebase Admin SDK service-account JSON found "
            "(set FCM_SERVICE_ACCOUNT_PATH or place *-firebase-adminsdk-*.json in project root)."
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception as exc:
        logger.warning("firebase-admin import failed: %s", exc)
        return False

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        _fcm_initialized = True
        logger.info("FCM initialized using %s", sa_path)
        return True
    except Exception as exc:
        # Log on each failure so misconfig is visible — but don't cache the failure,
        # so a transient issue (file perms, missing file) recovers without restart.
        logger.exception("Failed to initialize Firebase Admin SDK: %s", exc)
        return False


def _send_fcm_push(
    token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Send a Firebase Cloud Messaging push notification to one device token.
    Returns True on success.
    """
    if not token:
        return False
    if not _ensure_fcm_initialized():
        return False

    try:
        from firebase_admin import messaging
    except Exception as exc:
        logger.warning("firebase-admin messaging import failed: %s", exc)
        return False

    payload = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=payload,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="delycart_high",
                sound="default",
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1),
            ),
        ),
    )

    try:
        message_id = messaging.send(message)
        logger.info("FCM sent: %s | title=%r", message_id, title)
        return True
    except Exception as exc:
        logger.warning("FCM send failed (title=%r): %s", title, exc)
        return False


def create_notification(
    db: Session,
    user_id: Union[str, UUID],
    type: str,
    title: str,
    message: str,
    data: Optional[dict] = None,
) -> Notification:
    """
    Create an in-app notification for a CUSTOMER user and push to their device.

    type: "kyc" | "order" | "delivery" | "payment" | "welcome" | "promo".
    data: optional payload for navigation, e.g. {"order_id": ..., "order_number": ...}.

    Always commits and returns the persisted record. FCM failures are logged but don't raise.
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

    try:
        user = db.query(User).filter(User.id == str(uid)).first()
        if user and user.fcm_token:
            _send_fcm_push(
                token=user.fcm_token,
                title=title,
                body=message,
                data={
                    "type": type,
                    "notification_id": str(notif.id),
                    **(data or {}),
                },
            )
    except Exception as exc:
        logger.warning("Failed to send FCM to user %s: %s", uid, exc)

    return notif


def notify_delivery_person(
    db: Session,
    delivery_person_id: Union[str, UUID],
    type: str,
    title: str,
    message: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Push a notification to a delivery person via FCM.

    Delivery persons don't currently have an in-app inbox table — they receive
    only the FCM push. Returns True if the push was attempted with a valid token.
    """
    try:
        dp = db.query(DeliveryPerson).filter(
            DeliveryPerson.id == str(delivery_person_id)
        ).first()
    except Exception as exc:
        logger.warning("notify_delivery_person query failed: %s", exc)
        return False

    if not dp or not getattr(dp, "fcm_token", None):
        return False

    return _send_fcm_push(
        token=dp.fcm_token,
        title=title,
        body=message,
        data={
            "type": type,
            "audience": "delivery",
            **(data or {}),
        },
    )
