"""
Admin Order Returns Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.schemas.common import ResponseModel
from app.api.admin_deps import get_current_active_admin, require_manager_or_above
from app.models.order_return import OrderReturn
from app.models.order import Order
from app.models.delivery_person import DeliveryPerson

router = APIRouter()

VALID_STATUSES = {"requested", "approved", "rejected", "pickup_assigned", "picked_up", "received_at_hub"}


def _serialize_return(ret: OrderReturn, order: Optional[Order] = None) -> dict:
    o = order or ret.order
    return {
        "returnId": ret.id,
        "orderId": ret.order_id,
        "orderNumber": o.order_number if o else None,
        "userId": ret.user_id,
        "customerName": (ret.user.name if ret.user else None) or (o.user.name if o and o.user else "Customer"),
        "customerPhone": (ret.user.phone if ret.user else None) or (o.user.phone if o and o.user else None),
        "status": ret.status,
        "reason": ret.reason,
        "mediaUrls": ret.media_urls or [],
        "bankAccountNumber": ret.bank_account_number,
        "bankIfscCode": ret.bank_ifsc_code,
        "bankAccountHolder": ret.bank_account_holder,
        "bankName": ret.bank_name,
        "adminNotes": ret.admin_notes,
        "deliveryPersonId": ret.delivery_person_id,
        "deliveryPersonName": ret.delivery_person.name if ret.delivery_person else None,
        "pickedUpAt": ret.picked_up_at.isoformat() if ret.picked_up_at else None,
        "receivedAtHubAt": ret.received_at_hub_at.isoformat() if ret.received_at_hub_at else None,
        "orderTotal": float(o.total_amount or o.total or 0) if o else None,
        "paymentMethod": o.payment_method if o else None,
        "createdAt": ret.created_at.isoformat(),
        "updatedAt": ret.updated_at.isoformat(),
    }


@router.get("", response_model=ResponseModel)
def list_returns(
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin=Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """List all return requests with optional status filter."""
    query = db.query(OrderReturn)
    if status and status in VALID_STATUSES:
        query = query.filter(OrderReturn.status == status)
    total = query.count()
    returns = query.order_by(desc(OrderReturn.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return ResponseModel(
        success=True,
        data={
            "returns": [_serialize_return(r) for r in returns],
            "total": total,
            "page": page,
            "pageSize": page_size,
        },
        message="Returns retrieved",
    )


@router.get("/{return_id}", response_model=ResponseModel)
def get_return(
    return_id: str,
    admin=Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    ret = db.query(OrderReturn).filter(OrderReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    return ResponseModel(success=True, data=_serialize_return(ret), message="Return retrieved")


@router.put("/{return_id}/approve", response_model=ResponseModel)
def approve_return(
    return_id: str,
    payload: dict,
    admin=Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Approve a return request."""
    ret = db.query(OrderReturn).filter(OrderReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if ret.status not in ("requested",):
        raise HTTPException(status_code=400, detail=f"Cannot approve a return in '{ret.status}' status")

    ret.status = "approved"
    ret.admin_notes = (payload.get("notes") or "").strip() or None
    ret.reviewed_by = str(admin.id)
    ret.reviewed_at = datetime.utcnow()
    db.commit()

    if ret.user_id:
        try:
            from app.utils.notification_helper import create_notification
            create_notification(
                db=db,
                user_id=ret.user_id,
                type="order",
                title="Your return request has been approved",
                message="A delivery person will be assigned to collect the item from you.",
                data={"return_id": ret.id, "order_id": ret.order_id},
            )
        except Exception:
            db.rollback()

    return ResponseModel(success=True, data={"status": ret.status}, message="Return approved")


@router.put("/{return_id}/reject", response_model=ResponseModel)
def reject_return(
    return_id: str,
    payload: dict,
    admin=Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Reject a return request."""
    ret = db.query(OrderReturn).filter(OrderReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if ret.status not in ("requested",):
        raise HTTPException(status_code=400, detail=f"Cannot reject a return in '{ret.status}' status")

    notes = (payload.get("notes") or "").strip()
    if not notes:
        raise HTTPException(status_code=400, detail="Rejection reason (notes) is required")

    ret.status = "rejected"
    ret.admin_notes = notes
    ret.reviewed_by = str(admin.id)
    ret.reviewed_at = datetime.utcnow()
    db.commit()

    if ret.user_id:
        try:
            from app.utils.notification_helper import create_notification
            create_notification(
                db=db,
                user_id=ret.user_id,
                type="order",
                title="Your return request was not approved",
                message=notes,
                data={"return_id": ret.id, "order_id": ret.order_id},
            )
        except Exception:
            db.rollback()

    return ResponseModel(success=True, data={"status": ret.status}, message="Return rejected")


@router.put("/{return_id}/assign-pickup", response_model=ResponseModel)
def assign_pickup_delivery(
    return_id: str,
    payload: dict,
    admin=Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Assign a delivery person to collect the return from the customer."""
    ret = db.query(OrderReturn).filter(OrderReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if ret.status not in ("approved",):
        raise HTTPException(status_code=400, detail="Return must be approved before assigning pickup")

    delivery_person_id = (payload.get("delivery_person_id") or "").strip()
    if not delivery_person_id:
        raise HTTPException(status_code=400, detail="delivery_person_id is required")

    dp = db.query(DeliveryPerson).filter(DeliveryPerson.id == delivery_person_id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Delivery person not found")

    ret.delivery_person_id = delivery_person_id
    ret.status = "pickup_assigned"
    db.commit()

    if ret.user_id:
        try:
            from app.utils.notification_helper import create_notification
            create_notification(
                db=db,
                user_id=ret.user_id,
                type="order",
                title="Return pickup scheduled",
                message=f"Our delivery partner {dp.name} will collect the item from you shortly.",
                data={"return_id": ret.id, "order_id": ret.order_id},
            )
        except Exception:
            db.rollback()

    return ResponseModel(
        success=True,
        data={"status": ret.status, "deliveryPersonName": dp.name},
        message="Pickup assigned successfully",
    )
