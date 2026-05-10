import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderCancel, OrderTracking
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services.order_service import generate_order_number, calculate_order_totals
from app.utils.pagination import paginate
from app.utils.invoice import build_invoice_data
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

router = APIRouter()


COD_ALIASES = {"cod", "cash", "cash_on_delivery", "cash-on-delivery"}


def _normalize_payment_method(raw_method: Optional[str]) -> str:
    method = str(raw_method or "").strip().lower()
    if method in COD_ALIASES:
        return "cod"
    raise HTTPException(
        status_code=400,
        detail="Only cash on delivery is supported right now. Use payment_method='cod'.",
    )


def _parse_optional_cancel_body(raw: bytes) -> OrderCancel:
    """Accept missing/empty body and JSON null (clients often POST with no usable JSON)."""
    if not raw or not raw.strip():
        return OrderCancel()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON body")
    if data is None:
        return OrderCancel()
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Cancel body must be a JSON object")
    return OrderCancel.model_validate(data)


@router.post("", response_model=ResponseModel, status_code=201)
def create_order(
    order_data: OrderCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order"""
    # Handle delivery address - support both delivery_location_id and delivery_address
    delivery_address = order_data.delivery_address
    if order_data.delivery_location_id and not delivery_address:
        # Fetch delivery location and convert to address dict
        from app.models.delivery_location import DeliveryLocation
        # DeliveryLocation.id is String(36), DeliveryLocation.user_id is String(36), User.id is String(36)
        # Convert UUID path parameter to string for comparison
        location = db.query(DeliveryLocation).filter(
            DeliveryLocation.id == str(order_data.delivery_location_id),
            DeliveryLocation.user_id == str(current_user.id)
        ).first()
        if not location:
            raise HTTPException(status_code=404, detail="Delivery location not found")
        
        delivery_address = {
            "address_line1": location.address,
            "address_line2": location.landmark or "",
            "city": location.city,
            "state": location.state,
            "pincode": location.pincode,
            "type": location.type,
            "is_default": location.is_default
        }
    elif not delivery_address:
        raise HTTPException(status_code=400, detail="Either delivery_location_id or delivery_address is required")

    # Validate delivery pincode against global service location restrictions
    from app.models.settings import Settings as AppSettings
    service_setting = db.query(AppSettings).filter(AppSettings.key == "service_locations").first()
    if service_setting and isinstance(service_setting.value, dict) and service_setting.value.get("enabled"):
        locations = service_setting.value.get("locations", [])
        if locations:
            allowed_pincodes = {loc["pincode"].strip() for loc in locations if loc.get("pincode")}
            order_pincode = str(delivery_address.get("pincode", "")).strip()
            if order_pincode and order_pincode not in allowed_pincodes:
                raise HTTPException(
                    status_code=400,
                    detail="Delivery is not available in your location. We don't serve your pincode yet."
                )

    # Calculate totals
    items_data = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_data.items]
    totals = calculate_order_totals(items_data, db)
    
    # Resolve division_id from first product (for Kitchen / Grocery)
    division_id = None
    if order_data.items:
        first_product = db.query(Product).filter(Product.id == str(order_data.items[0].product_id)).first()
        if first_product and first_product.division_id:
            division_id = str(first_product.division_id)

    normalized_payment_method = _normalize_payment_method(order_data.payment_method)

    order = Order(
        order_number=generate_order_number(),
        user_id=str(current_user.id),
        division_id=division_id,
        status=OrderStatus.PENDING,
        delivery_address=delivery_address,
        payment_method=normalized_payment_method,
        payment_details=order_data.payment_details,
        subtotal=totals["subtotal"],
        discount=totals["discount"],
        delivery_charge=totals["delivery_charge"],
        tax=totals["tax"],
        total=totals["total"],
        total_amount=totals["total"],
    )
    db.add(order)
    db.flush()

    from app.utils.product_pricing import (
        assert_tier_allowed,
        customer_price_with_commission,
        normalize_price_tier,
    )

    order_items_data = []
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        tier = normalize_price_tier(item.price_option_key)
        assert_tier_allowed(product, tier)
        price = customer_price_with_commission(product, tier)

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


@router.get("/{order_id}/invoice", response_model=ResponseModel)
def get_invoice(
    order_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invoice for an order (same structure as admin invoice)."""
    from uuid import UUID as UUIDType

    order_id_str = str(order_id).strip()
    try:
        UUIDType(order_id_str)
        order = db.query(Order).filter(
            Order.id == order_id_str,
            Order.user_id == str(current_user.id)
        ).first()
    except (ValueError, AttributeError):
        order = db.query(Order).filter(
            Order.order_number == order_id_str,
            Order.user_id == str(current_user.id)
        ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    invoice_data = build_invoice_data(order, current_user, db)
    return ResponseModel(
        success=True,
        data=invoice_data,
        message="Invoice fetched successfully"
    )


@router.post("/{order_id}/cancel", response_model=ResponseModel)
async def cancel_order(
    request: Request,
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Customer-initiated cancel.
    Allowed only before the order is shipped; restores product stock.
    Body is optional: omit, `null`, `{}`, or `{"reason": "..."}`.
    """
    payload = _parse_optional_cancel_body(await request.body())
    order_id_str = str(order_id)
    order = db.query(Order).filter(
        Order.id == order_id_str,
        Order.user_id == str(current_user.id)
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in (OrderStatus.CANCELLED, OrderStatus.CANCELED):
        raise HTTPException(status_code=400, detail="Order is already cancelled")

    if order.status in (
        OrderStatus.DELIVERED,
        OrderStatus.COMPLETED,
        OrderStatus.SHIPPED,
        OrderStatus.OUT_FOR_DELIVERY,
    ):
        raise HTTPException(
            status_code=400,
            detail="This order can no longer be cancelled. Contact support if you need help.",
        )

    # Restore stock
    order_items = db.query(OrderItem).filter(OrderItem.order_id == str(order.id)).all()
    for item in order_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            if product.stock_quantity:
                product.stock_quantity += item.quantity
            elif hasattr(product, "stock") and product.stock:
                product.stock += item.quantity

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    order.cancelled_reason = payload.reason
    db.commit()

    # Optional status history (changed_by=None for customer action)
    from uuid import UUID as UUIDType
    from app.models.order_status_history import OrderStatusHistory

    try:
        order_uuid = UUIDType(order_id_str)
        status_history = OrderStatusHistory(
            order_id=order_uuid,
            status=OrderStatus.CANCELLED,
            changed_by=None,
            notes=payload.reason or "Cancelled by customer",
        )
        db.add(status_history)
        db.commit()
    except Exception:
        db.rollback()

    if order.user_id:
        try:
            from app.utils.notification_helper import create_notification

            create_notification(
                db=db,
                user_id=order.user_id,
                type="order",
                title=f"Order #{order.order_number} cancelled",
                message="Your order has been cancelled.",
                data={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "status": "cancelled",
                },
            )
        except Exception:
            db.rollback()

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

