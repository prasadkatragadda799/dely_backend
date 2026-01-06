"""
Admin Order Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.models.product import Product
from app.models.order_status_history import OrderStatusHistory
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.pagination import paginate
from app.models.admin import Admin

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    sort: Optional[str] = Query("created_at", pattern="^(created_at|total_amount|status)$"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all orders with filters"""
    query = db.query(Order)
    
    # Apply filters
    if status:
        try:
            order_status = OrderStatus(status)
            query = query.filter(Order.status == order_status)
        except ValueError:
            pass
    
    if payment_method:
        query = query.filter(Order.payment_method == payment_method)
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
    
    if search:
        query = query.filter(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Order.user.has(User.name.ilike(f"%{search}%")),
                Order.user.has(User.business_name.ilike(f"%{search}%"))
            )
        )
    
    # Apply sorting
    if sort == "total_amount":
        order_by = Order.total_amount.asc() if order == "asc" else Order.total_amount.desc()
    elif sort == "status":
        order_by = Order.status.asc() if order == "asc" else Order.status.desc()
    else:
        order_by = Order.created_at.desc() if order == "desc" else Order.created_at.asc()
    
    query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    orders = query.offset(offset).limit(limit).all()
    
    # Format response
    order_list = []
    for o in orders:
        order_data = {
            "id": o.id,
            "orderNumber": o.order_number,
            "user": {
                "id": o.user.id if o.user else None,
                "name": o.user.name if o.user else "Unknown",
                "businessName": o.user.business_name if o.user else None
            } if o.user else None,
            "status": o.status.value,
            "itemsCount": len(o.order_items),
            "totalAmount": float(o.total_amount),
            "paymentMethod": o.payment_method,
            "paymentStatus": o.payment_status,
            "createdAt": o.created_at,
            "deliveryDate": None  # Calculate based on status
        }
        order_list.append(order_data)
    
    return ResponseModel(
        success=True,
        data={
            "orders": order_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        },
        message="Orders retrieved successfully"
    )


@router.get("/{order_id}", response_model=ResponseModel)
async def get_order(
    order_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Format order items
    items = []
    for item in order.order_items:
        items.append({
            "id": item.id,
            "product": {
                "id": item.product.id if item.product else None,
                "name": item.product_name,
                "imageUrl": item.product_image_url
            } if item.product else {
                "name": item.product_name,
                "imageUrl": item.product_image_url
            },
            "quantity": item.quantity,
            "unitPrice": float(item.unit_price),
            "subtotal": float(item.subtotal)
        })
    
    # Format status history
    status_history = []
    for history in order.status_history:
        status_history.append({
            "status": history.status.value,
            "changedBy": str(history.changed_by) if history.changed_by else None,
            "notes": history.notes,
            "createdAt": history.created_at
        })
    
    order_data = {
        "id": order.id,
        "orderNumber": order.order_number,
        "user": {
            "id": order.user.id if order.user else None,
            "name": order.user.name if order.user else "Unknown",
            "email": order.user.email if order.user else None,
            "phone": order.user.phone if order.user else None,
            "businessName": order.user.business_name if order.user else None
        } if order.user else None,
        "items": items,
        "subtotal": float(order.subtotal),
        "discount": float(order.discount),
        "deliveryCharge": float(order.delivery_charge),
        "tax": float(order.tax),
        "totalAmount": float(order.total_amount),
        "deliveryAddress": order.delivery_address,
        "status": order.status.value,
        "paymentMethod": order.payment_method,
        "paymentStatus": order.payment_status,
        "trackingNumber": order.tracking_number,
        "notes": order.notes,
        "statusHistory": status_history,
        "createdAt": order.created_at,
        "updatedAt": order.updated_at
    }
    
    return ResponseModel(
        success=True,
        data=order_data,
        message="Order retrieved successfully"
    )


@router.put("/{order_id}/status", response_model=ResponseModel)
async def update_order_status(
    order_id: UUID,
    status_data: dict,  # {"status": "confirmed", "notes": "..."}
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update order status"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    new_status = status_data.get("status")
    notes = status_data.get("notes")
    
    try:
        order_status = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {new_status}"
        )
    
    old_status = order.status
    order.status = order_status
    db.commit()
    
    # Create status history entry
    status_history = OrderStatusHistory(
        order_id=order_id,
        status=order_status,
        changed_by=admin.id,
        notes=notes
    )
    db.add(status_history)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="order_status_updated",
        entity_type="order",
        entity_id=order_id,
        details={
            "old_status": old_status.value,
            "new_status": new_status,
            "notes": notes
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": order.id,
            "status": order.status.value,
            "statusHistory": [{
                "status": sh.status.value,
                "createdAt": sh.created_at
            } for sh in order.status_history]
        },
        message="Order status updated successfully"
    )


@router.post("/{order_id}/cancel", response_model=ResponseModel)
async def cancel_order(
    order_id: UUID,
    cancel_data: dict,  # {"reason": "..."}
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Order is already cancelled")
    
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Cannot cancel a delivered order")
    
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    order.cancelled_reason = cancel_data.get("reason")
    db.commit()
    
    # Create status history
    status_history = OrderStatusHistory(
        order_id=order_id,
        status=OrderStatus.CANCELLED,
        changed_by=admin.id,
        notes=cancel_data.get("reason")
    )
    db.add(status_history)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="order_cancelled",
        entity_type="order",
        entity_id=order_id,
        details={"reason": cancel_data.get("reason")},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Order cancelled successfully"
    )

