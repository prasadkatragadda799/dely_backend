from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderCancel, OrderTracking
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services.order_service import generate_order_number, calculate_order_totals
from app.utils.pagination import paginate
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

router = APIRouter()


@router.post("", response_model=ResponseModel, status_code=201)
def create_order(
    order_data: OrderCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order"""
    # Calculate totals
    items_data = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_data.items]
    totals = calculate_order_totals(items_data, db)
    
    # Create order
    order = Order(
        order_number=generate_order_number(),
        user_id=str(current_user.id),
        status=OrderStatus.PENDING,
        delivery_address=order_data.delivery_address,
        payment_method=order_data.payment_method,
        payment_details=order_data.payment_details,
        subtotal=totals["subtotal"],
        discount=totals["discount"],
        delivery_charge=totals["delivery_charge"],
        tax=totals["tax"],
        total_amount=totals["total"]
    )
    db.add(order)
    db.flush()
    
    # Create order items and update stock
    order_items_data = []
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        # Use selling_price (or fallback to legacy price field)
        price = product.selling_price if product.selling_price else (product.price if hasattr(product, 'price') and product.price else Decimal('0.00'))
        
        order_item = OrderItem(
            order_id=str(order.id),
            product_id=str(item.product_id),
            quantity=item.quantity,
            price=price,
            subtotal=price * item.quantity
        )
        db.add(order_item)
        
        # Update product stock
        if product.stock_quantity:
            product.stock_quantity -= item.quantity
        elif hasattr(product, 'stock') and product.stock:
            product.stock -= item.quantity
        order_items_data.append(order_item)
    
    db.commit()
    db.refresh(order)
    
    # Clear cart
    from app.models.cart import Cart
    db.query(Cart).filter(Cart.user_id == str(current_user.id)).delete()
    db.commit()
    
    return ResponseModel(
        success=True,
        data=OrderResponse.model_validate(order),
        message="Order created successfully"
    )


@router.get("", response_model=ResponseModel)
def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, alias="status"),  # Support both status and status_filter
    status_filter: Optional[str] = None,  # Keep for backward compatibility
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's orders"""
    query = db.query(Order).filter(Order.user_id == str(current_user.id))
    
    # Use status if provided, otherwise fallback to status_filter
    status_value = status or status_filter
    if status_value:
        try:
            status_enum = OrderStatus(status_value)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            pass
    
    total = query.count()
    offset = (page - 1) * limit
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    return ResponseModel(
        success=True,
        data={
            "items": [OrderListResponse.model_validate(o) for o in orders],
            "pagination": paginate(orders, page, limit, total)
        }
    )


@router.get("/{order_id}", response_model=ResponseModel)
def get_order(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order details"""
    order = db.query(Order).filter(
        Order.id == str(order_id),
        Order.user_id == str(current_user.id)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return ResponseModel(
        success=True,
        data=OrderResponse.model_validate(order)
    )


@router.post("/{order_id}/cancel", response_model=ResponseModel)
def cancel_order(
    order_id: UUID,
    cancel_data: OrderCancel,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    order = db.query(Order).filter(
        Order.id == str(order_id),
        Order.user_id == str(current_user.id)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status {order.status}"
        )
    
    # Restore stock
    order_items = db.query(OrderItem).filter(OrderItem.order_id == str(order.id)).all()
    for item in order_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            if product.stock_quantity:
                product.stock_quantity += item.quantity
            elif hasattr(product, 'stock') and product.stock:
                product.stock += item.quantity
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    
    return ResponseModel(success=True, message="Order cancelled successfully")


@router.get("/{order_id}/track", response_model=ResponseModel)
def track_order(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track order status"""
    order = db.query(Order).filter(
        Order.id == str(order_id),
        Order.user_id == str(current_user.id)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create status history
    status_history = [
        {"status": "pending", "timestamp": order.created_at.isoformat(), "message": "Order placed"},
    ]
    
    if order.status != OrderStatus.PENDING:
        status_history.append({
            "status": order.status.value,
            "timestamp": order.updated_at.isoformat(),
            "message": f"Order {order.status.value}"
        })
    
    estimated_delivery = None
    if order.status not in [OrderStatus.CANCELLED, OrderStatus.DELIVERED]:
        estimated_delivery = (order.created_at + timedelta(days=3)).isoformat()
    
    tracking = OrderTracking(
        order_number=order.order_number,
        status=order.status.value,
        status_history=status_history,
        estimated_delivery=estimated_delivery
    )
    
    return ResponseModel(success=True, data=tracking)

