from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.schemas.common import ResponseModel
from app.models.notification import Notification
from app.utils.pagination import paginate
from uuid import UUID
from typing import Optional

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread: Optional[bool] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread is not None:
        query = query.filter(Notification.is_read == (not unread))
    
    total = query.count()
    offset = (page - 1) * limit
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return ResponseModel(
        success=True,
        data={
            "notifications": [NotificationResponse.model_validate(n) for n in notifications],
            "unread_count": unread_count,
            "pagination": paginate(notifications, page, limit, total)
        }
    )


@router.put("/{notification_id}/read", response_model=ResponseModel)
def mark_notification_read(
    notification_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return ResponseModel(success=True, message="Notification marked as read")


@router.put("/read-all", response_model=ResponseModel)
def mark_all_read(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    return ResponseModel(success=True, message="All notifications marked as read")

