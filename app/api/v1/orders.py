import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderCancel, OrderTracking
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.services.order_service import generate_order_number, calculate_order_totals
from app.utils.packaging_label import format_variant_packaging_line
from app.utils.pagination import paginate
from app.utils.invoice import build_invoice_data
from app.config import settings
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

    # Calculate totals. Pass price_option_key + variant_id through so the totals are
    # computed with the SAME price the line items use (variant price or the chosen
    # tier), keeping order totals == sum of line items.
    items_data = [
        {
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price_option_key": item.price_option_key,
            "variant_id": item.variant_id,
        }
        for item in order_data.items
    ]
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
        variant_customer_price,
    )

    order_items_data = []
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        variant = None
        variant_label = None
        if item.variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == str(item.variant_id),
                ProductVariant.product_id == str(item.product_id),
            ).first()
            if not variant:
                raise HTTPException(
                    status_code=404,
                    detail=f"Variant {item.variant_id} not found for product {item.product_id}",
                )

        if variant is not None:
            price = variant_customer_price(product, variant)
            variant_label = format_variant_packaging_line(
                getattr(variant, "packaging_label_type", None),
                getattr(variant, "set_pcs", None),
                getattr(variant, "weight", None),
            )
        else:
            tier = normalize_price_tier(item.price_option_key)
            assert_tier_allowed(product, tier)
            price = customer_price_with_commission(product, tier)

        order_item = OrderItem(
            order_id=str(order.id),
            product_id=str(item.product_id),
            variant_id=str(variant.id) if variant is not None else None,
            variant_label=variant_label,
            product_name=product.name,
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

    # Serialize the response NOW while the session is guaranteed clean —
    # before cart deletion and notification, either of which can leave the
    # session in InFailedSqlTransaction if they fail.
    response_data = OrderResponse.model_validate(order)

    # Clear cart
    from app.models.cart import Cart
    db.query(Cart).filter(Cart.user_id == str(current_user.id)).delete()
    db.commit()

    # Notify the customer that their order has been received.
    try:
        from app.utils.notification_helper import create_notification
        create_notification(
            db=db,
            user_id=str(current_user.id),
            type="order",
            title=f"Order #{order.order_number} placed",
            message=f"We've received your order of ₹{totals['total']:.2f}. We'll keep you posted on delivery.",
            data={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "status": "pending",
            },
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return ResponseModel(
        success=True,
        data=response_data,
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


RETURN_WINDOW_DAYS = 7
ALLOWED_MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.mp4', '.mov', '.avi', '.mkv', '.webm'}
MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50 MB (videos can be large)


def _return_deadline_exceeded(order: Order) -> bool:
    """True if the 7-day return window has closed."""
    reference = order.updated_at or order.created_at
    return (datetime.utcnow() - reference).days > RETURN_WINDOW_DAYS


@router.post("/{order_id}/return", response_model=ResponseModel, status_code=201)
async def initiate_return(
    order_id: UUID,
    request: Request,
    reason: str = Form(..., min_length=5),
    bank_account_number: Optional[str] = Form(default=None),
    bank_ifsc_code: Optional[str] = Form(default=None),
    bank_account_holder: Optional[str] = Form(default=None),
    bank_name: Optional[str] = Form(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate a return request for a delivered order within 7 days.
    Accepts multipart/form-data with reason, optional bank details (for COD),
    and up to 5 media files (images + 1 video).
    """
    from app.models.order_return import OrderReturn
    from pathlib import Path
    import uuid as uuid_module

    order_id_str = str(order_id)
    order = db.query(Order).filter(
        Order.id == order_id_str,
        Order.user_id == str(current_user.id),
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status.value not in ("delivered", "completed"):
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")

    if _return_deadline_exceeded(order):
        raise HTTPException(status_code=400, detail=f"Return window of {RETURN_WINDOW_DAYS} days has passed")

    existing = db.query(OrderReturn).filter(OrderReturn.order_id == order_id_str).first()
    if existing:
        raise HTTPException(status_code=409, detail="A return request already exists for this order")

    # Persist media files
    media_urls: List[Dict[str, str]] = []
    if files:
        upload_files = [f for f in files if f and f.filename]
        if len(upload_files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 media files allowed")

        return_dir_id = str(uuid_module.uuid4())
        base_url = settings.CDN_BASE_URL or str(request.base_url).rstrip("/")

        for f in upload_files:
            ext = Path(f.filename).suffix.lower() if f.filename else ""
            if ext not in ALLOWED_MEDIA_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
            content = await f.read()
            if len(content) > MAX_MEDIA_SIZE:
                raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")
            media_type = "video" if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"} else "image"
            unique_name = f"{uuid_module.uuid4()}{ext}"
            upload_dir = Path(settings.UPLOAD_DIR) / "return" / return_dir_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            with open(upload_dir / unique_name, "wb") as fp:
                fp.write(content)
            media_urls.append({"url": f"{base_url}/uploads/return/{return_dir_id}/{unique_name}", "type": media_type})

    # Media evidence is mandatory: at least one photo and one video of the item.
    has_image = any(m.get("type") == "image" for m in media_urls)
    has_video = any(m.get("type") == "video" for m in media_urls)
    if not (has_image and has_video):
        raise HTTPException(
            status_code=400,
            detail="At least one photo and one video of the item are required for a return.",
        )

    return_request = OrderReturn(
        order_id=order_id_str,
        user_id=str(current_user.id),
        reason=reason.strip(),
        media_urls=media_urls or None,
        bank_account_number=bank_account_number.strip() if bank_account_number else None,
        bank_ifsc_code=bank_ifsc_code.strip().upper() if bank_ifsc_code else None,
        bank_account_holder=bank_account_holder.strip() if bank_account_holder else None,
        bank_name=bank_name.strip() if bank_name else None,
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)

    try:
        from app.utils.notification_helper import create_notification
        create_notification(
            db=db,
            user_id=str(current_user.id),
            type="order",
            title=f"Return request submitted for Order #{order.order_number}",
            message="We've received your return request and will review it shortly.",
            data={"order_id": order_id_str, "return_id": return_request.id},
        )
    except Exception:
        db.rollback()

    return ResponseModel(
        success=True,
        data={"returnId": return_request.id, "status": return_request.status},
        message="Return request submitted successfully",
    )


@router.get("/{order_id}/return", response_model=ResponseModel)
def get_return_status(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the return request status for an order."""
    from app.models.order_return import OrderReturn

    order_id_str = str(order_id)
    order = db.query(Order).filter(
        Order.id == order_id_str,
        Order.user_id == str(current_user.id),
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    ret = db.query(OrderReturn).filter(OrderReturn.order_id == order_id_str).first()
    if not ret:
        raise HTTPException(status_code=404, detail="No return request found for this order")

    is_cod = (order.payment_method or "").lower() in COD_ALIASES
    return ResponseModel(
        success=True,
        data={
            "returnId": ret.id,
            "status": ret.status,
            "reason": ret.reason,
            "mediaUrls": ret.media_urls or [],
            "adminNotes": ret.admin_notes,
            "isCod": is_cod,
            "hasBankDetails": bool(ret.bank_account_number),
            "createdAt": ret.created_at.isoformat(),
            "updatedAt": ret.updated_at.isoformat(),
        },
        message="Return status retrieved",
    )
