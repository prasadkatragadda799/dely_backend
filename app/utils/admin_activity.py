"""
Admin Activity Logging Utility
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import Request
from app.models.admin_activity_log import AdminActivityLog
from datetime import datetime, date
from decimal import Decimal


def log_admin_activity(
    db: Session,
    admin_id: Optional[UUID],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log admin activity to the database
    
    Args:
        db: Database session
        admin_id: ID of the admin performing the action
        action: Action name (e.g., 'product_created', 'order_status_updated')
        entity_type: Type of entity (e.g., 'product', 'order', 'user')
        entity_id: ID of the entity being acted upon
        details: Additional details as JSON
        request: FastAPI request object to extract IP and user agent
    """
    ip_address = None
    user_agent = None
    
    if request:
        # Get client IP
        if request.client:
            ip_address = request.client.host
        # Get user agent
        user_agent = request.headers.get("user-agent")
    
    def _to_json_safe(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            # Keep numeric semantics for JSON columns.
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {str(k): _to_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_to_json_safe(v) for v in value]
        # Last resort: avoid raising due to non-serializable custom objects.
        return str(value)

    safe_details = _to_json_safe(details) if details is not None else None

    activity_log = AdminActivityLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=safe_details,
        ip_address=ip_address,
        user_agent=user_agent
    )

    try:
        db.add(activity_log)
        db.commit()
    except Exception:
        # Activity logging should never break the primary business action.
        db.rollback()
        return None

    return activity_log

