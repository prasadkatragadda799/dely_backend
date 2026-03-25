"""
Delivery Orders Endpoints
For delivery personnel to view and manage assigned orders
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError, IntegrityError, StatementError
from sqlalchemy import text
from typing import List, Optional
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.delivery import DeliveryOrderResponse, DeliveryStatusUpdate, LocationUpdate, AvailabilityRequest
from app.models.order import Order, OrderStatus
from app.models.delivery_person import DeliveryPerson
from app.api.v1.delivery_auth import get_current_delivery_person
from datetime import datetime

router = APIRouter()


def _supports_out_for_delivery(db: Session) -> bool:
    """Check if DB enum includes OUT_FOR_DELIVERY literal."""
    try:
        rows = db.execute(
            text("SELECT unnest(enum_range(NULL::orderstatus))::text")
        ).fetchall()
        allowed = {str(row[0]).upper() for row in rows}
        return "OUT_FOR_DELIVERY" in allowed
    except Exception:
        # If enum introspection fails, use conservative fallback.
        return False


@router.get("/assigned", response_model=ResponseModel)
async def get_assigned_orders(
    status: Optional[str] = None,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """
    Get orders assigned to current delivery person.
    Status filter: pending, picked_up, in_transit, delivered
    """
    query = db.query(Order).filter(
        Order.delivery_person_id == delivery_person.id
    )
    
    # Filter by status if provided
    if status:
        if status == "pending":
            query = query.filter(Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING]))
        elif status == "picked_up":
            query = query.filter(Order.status == OrderStatus.SHIPPED)
        elif status == "in_transit":
            if _supports_out_for_delivery(db):
                query = query.filter(Order.status == OrderStatus.OUT_FOR_DELIVERY)
            else:
                query = query.filter(Order.status == OrderStatus.SHIPPED)
        elif status == "delivered":
            query = query.filter(Order.status == OrderStatus.DELIVERED)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Format orders for delivery app
    formatted_orders = []
    for order in orders:
        # Get customer info
        customer_name = "Customer"
        customer_phone = "N/A"
        if order.user:
            customer_name = order.user.name
            customer_phone = order.user.phone or "N/A"
        
        # Get delivery address
        delivery_address = order.delivery_address or {}
        
        # Get items
        items = []
        for item in order.order_items:
            if item.product:
                items.append({
                    "productName": item.product.name,
                    "quantity": item.quantity,
                    "price": float(item.price) if item.price else 0.0
                })
        
        formatted_orders.append({
            "id": order.id,
            "orderNumber": order.order_number,
            "order_number": order.order_number,
            "status": order.status.value,
            "customerName": customer_name,
            "customer_name": customer_name,
            "customerPhone": customer_phone,
            "customer_phone": customer_phone,
            "deliveryAddress": delivery_address,
            "delivery_address": delivery_address,
            "items": items,
            "totalAmount": float(order.total_amount),
            "total_amount": float(order.total_amount),
            "createdAt": order.created_at.isoformat() if order.created_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None
        })
    
    return ResponseModel(
        success=True,
        data={
            "orders": formatted_orders,
            "total": len(formatted_orders)
        },
        message="Assigned orders retrieved successfully"
    )


@router.get("/{order_id}", response_model=ResponseModel)
async def get_order_details(
    order_id: str,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_person_id == delivery_person.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or not assigned to you"
        )
    
    # Format order details
    customer_name = order.user.name if order.user else "Customer"
    customer_phone = order.user.phone if order.user else "N/A"
    delivery_address = order.delivery_address or {}
    
    items = []
    for item in order.order_items:
        if item.product:
            items.append({
                "id": item.id,
                "productName": item.product.name,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.price) if item.price else 0.0,
                "subtotal": float(item.subtotal) if item.subtotal else 0.0
            })
    
    order_data = {
        "id": order.id,
        "orderNumber": order.order_number,
        "order_number": order.order_number,
        "status": order.status.value,
        "customerName": customer_name,
        "customer_name": customer_name,
        "customerPhone": customer_phone,
        "customer_phone": customer_phone,
        "deliveryAddress": delivery_address,
        "delivery_address": delivery_address,
        "items": items,
        "subtotal": float(order.subtotal),
        "deliveryCharge": float(order.delivery_charge) if order.delivery_charge else 0.0,
        "delivery_charge": float(order.delivery_charge) if order.delivery_charge else 0.0,
        "totalAmount": float(order.total_amount),
        "total_amount": float(order.total_amount),
        "paymentMethod": order.payment_method,
        "payment_method": order.payment_method,
        "paymentStatus": order.payment_status,
        "payment_status": order.payment_status,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "notes": order.notes
    }
    
    return ResponseModel(
        success=True,
        data=order_data,
        message="Order details retrieved successfully"
    )


@router.put("/{order_id}/status", response_model=ResponseModel)
async def update_delivery_status(
    order_id: str,
    status_update: DeliveryStatusUpdate,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Update order delivery status"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.delivery_person_id == delivery_person.id
        ).first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or not assigned to you"
            )

        requested_status = (status_update.status or "").strip().lower()
        supports_out_for_delivery = _supports_out_for_delivery(db)

        # Map delivery-app statuses to DB enum literals
        status_mapping = {
            "picked_up": "SHIPPED",
            "shipped": "SHIPPED",
            "in_transit": "OUT_FOR_DELIVERY" if supports_out_for_delivery else "SHIPPED",
            "out_for_delivery": "OUT_FOR_DELIVERY" if supports_out_for_delivery else "SHIPPED",
            "arrived": "OUT_FOR_DELIVERY" if supports_out_for_delivery else "SHIPPED",
            "delivered": "DELIVERED",
        }

        if requested_status not in status_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_update.status}"
            )

        # Persist DB enum literal explicitly (matches live DB enum labels).
        db_status_value = status_mapping[requested_status]

        # Add notes if provided
        if status_update.notes:
            current_notes = order.notes or ""
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            order.notes = f"{current_notes}\n[{timestamp}] {requested_status}: {status_update.notes}".strip()

        # Bypass SQLAlchemy Enum name coercion and cast directly to DB enum literal.
        db.execute(
            text(
                "UPDATE orders "
                "SET status = CAST(:status AS orderstatus), updated_at = :updated_at "
                "WHERE id = :order_id"
            ),
            {
                "status": db_status_value,
                "updated_at": datetime.utcnow(),
                "order_id": order.id,
            },
        )
        db.commit()
        db.refresh(order)
        # Notify order owner about delivery status
        status_value = order.status.value if isinstance(order.status, OrderStatus) else str(order.status)
        if order.user_id:
            from app.utils.notification_helper import create_notification
            _type = "delivery" if status_value.lower() in ("out_for_delivery", "delivered", "shipped") else "order"
            _title = f"Order #{order.order_number} {status_value.replace('_', ' ')}"
            _msg = f"Your order has been updated to: {status_value.replace('_', ' ')}."
            try:
                create_notification(
                    db=db,
                    user_id=order.user_id,
                    type=_type,
                    title=_title,
                    message=_msg,
                    data={"order_id": str(order.id), "order_number": order.order_number, "status": status_value},
                )
            except Exception:
                pass

        # Update delivery person location if provided
        if status_update.latitude is not None and status_update.longitude is not None:
            delivery_person.current_latitude = status_update.latitude
            delivery_person.current_longitude = status_update.longitude
            delivery_person.last_location_update = datetime.utcnow()
            db.commit()

        return ResponseModel(
            success=True,
            data={
                "orderId": order.id,
                "status": status_value,
                "updatedAt": datetime.utcnow().isoformat()
            },
            message=f"Order status updated to {requested_status}"
        )
    except HTTPException:
        db.rollback()
        raise
    except (StatementError, DataError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update order status: {str(exc)}",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status due to server error: {str(exc)}",
        )


@router.post("/location", response_model=ResponseModel)
async def update_location(
    location: LocationUpdate,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Update delivery person's current location"""
    delivery_person.current_latitude = location.latitude
    delivery_person.current_longitude = location.longitude
    delivery_person.last_location_update = datetime.utcnow()
    db.commit()
    
    return ResponseModel(
        success=True,
        data={
            "latitude": delivery_person.current_latitude,
            "longitude": delivery_person.current_longitude,
            "updatedAt": delivery_person.last_location_update.isoformat()
        },
        message="Location updated successfully"
    )


@router.post("/availability", response_model=ResponseModel)
async def toggle_availability(
    request: AvailabilityRequest,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """
    Toggle delivery person's availability for new orders.
    Accepts JSON body: { "available": true/false }
    """
    try:
        # Update availability status
        delivery_person.is_available = request.available
        db.commit()
        db.refresh(delivery_person)
        
        return ResponseModel(
            success=True,
            message="Availability updated successfully",
            data={
                "isAvailable": delivery_person.is_available,
                "is_available": delivery_person.is_available,
                "deliveryPersonId": delivery_person.id
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update availability: {str(e)}"
        )
