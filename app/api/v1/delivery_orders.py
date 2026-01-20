"""
Delivery Orders Endpoints
For delivery personnel to view and manage assigned orders
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.delivery import DeliveryOrderResponse, DeliveryStatusUpdate, LocationUpdate
from app.models.order import Order, OrderStatus
from app.models.delivery_person import DeliveryPerson
from app.api.v1.delivery_auth import get_current_delivery_person
from datetime import datetime

router = APIRouter()


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
            query = query.filter(Order.status == OrderStatus.OUT_FOR_DELIVERY)
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
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_person_id == delivery_person.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or not assigned to you"
        )
    
    # Map delivery status to order status
    status_mapping = {
        "picked_up": OrderStatus.SHIPPED,
        "in_transit": OrderStatus.OUT_FOR_DELIVERY,
        "arrived": OrderStatus.OUT_FOR_DELIVERY,
        "delivered": OrderStatus.DELIVERED
    }
    
    if status_update.status not in status_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_update.status}"
        )
    
    # Update order status
    order.status = status_mapping[status_update.status]
    
    # Add notes if provided
    if status_update.notes:
        current_notes = order.notes or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        order.notes = f"{current_notes}\n[{timestamp}] {status_update.status}: {status_update.notes}".strip()
    
    db.commit()
    
    # Update delivery person location if provided
    if status_update.latitude and status_update.longitude:
        delivery_person.current_latitude = status_update.latitude
        delivery_person.current_longitude = status_update.longitude
        delivery_person.last_location_update = datetime.utcnow()
        db.commit()
    
    return ResponseModel(
        success=True,
        data={
            "orderId": order.id,
            "status": order.status.value,
            "updatedAt": datetime.utcnow().isoformat()
        },
        message=f"Order status updated to {status_update.status}"
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
    available: bool,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Toggle delivery person's availability for new orders"""
    delivery_person.is_available = available
    db.commit()
    
    return ResponseModel(
        success=True,
        data={
            "isAvailable": delivery_person.is_available,
            "is_available": delivery_person.is_available
        },
        message=f"Availability set to {'available' if available else 'unavailable'}"
    )
