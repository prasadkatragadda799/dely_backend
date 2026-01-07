"""
Admin Order Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.admin_order import OrderStatusUpdate, OrderCancel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_image import ProductImage
from app.models.order_status_history import OrderStatusHistory
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.pagination import paginate
from app.utils.invoice import get_seller_info
from app.models.admin import Admin

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    paymentMethod: Optional[str] = Query(None, alias="paymentMethod"),
    payment_method: Optional[str] = None,  # Alternative
    dateFrom: Optional[date] = Query(None, alias="dateFrom"),
    date_from: Optional[date] = None,  # Alternative
    dateTo: Optional[date] = Query(None, alias="dateTo"),
    date_to: Optional[date] = None,  # Alternative
    search: Optional[str] = None,
    sort: Optional[str] = Query("createdAt", alias="sort"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all orders with filters"""
    query = db.query(Order).options(joinedload(Order.user), joinedload(Order.order_items))
    
    # Apply filters
    if status:
        # Handle both "cancelled" and "canceled"
        if status.lower() == "canceled":
            status = "cancelled"
        try:
            order_status = OrderStatus(status)
            query = query.filter(Order.status == order_status)
        except ValueError:
            pass
    
    # Handle payment method (camelCase or snake_case)
    payment_method_value = paymentMethod or payment_method
    if payment_method_value:
        query = query.filter(Order.payment_method == payment_method_value)
    
    # Handle date filters (camelCase or snake_case)
    date_from_value = dateFrom or date_from
    date_to_value = dateTo or date_to
    if date_from_value:
        query = query.filter(Order.created_at >= datetime.combine(date_from_value, datetime.min.time()))
    if date_to_value:
        query = query.filter(Order.created_at <= datetime.combine(date_to_value, datetime.max.time()))
    
    if search:
        query = query.filter(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Order.id.ilike(f"%{search}%"),
                Order.user.has(User.name.ilike(f"%{search}%")),
                Order.user.has(User.business_name.ilike(f"%{search}%"))
            )
        )
    
    # Apply sorting (handle camelCase field names)
    sort_field = sort.lower() if sort else "created_at"
    if sort_field in ["createdat", "created_at", "orderdate", "order_date"]:
        order_by = Order.created_at.asc() if order == "asc" else Order.created_at.desc()
    elif sort_field in ["totalamount", "total_amount", "total", "amount"]:
        order_by = Order.total_amount.asc() if order == "asc" else Order.total_amount.desc()
    elif sort_field in ["ordernumber", "order_number", "orderid", "order_id"]:
        order_by = Order.order_number.asc() if order == "asc" else Order.order_number.desc()
    else:
        order_by = Order.created_at.desc() if order == "desc" else Order.created_at.asc()
    
    query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    orders = query.offset(offset).limit(limit).all()
    
    # Format response with all field name variations
    order_list = []
    for o in orders:
        # Calculate delivery date (3 days from creation, or based on status)
        delivery_date = None
        if o.status in [OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
            delivery_date = (o.created_at + timedelta(days=3)).isoformat() if o.created_at else None
        elif o.status == OrderStatus.DELIVERED or o.status == OrderStatus.COMPLETED:
            delivery_date = o.updated_at.isoformat() if o.updated_at else None
        
        # Get customer info
        customer = None
        customer_name = None
        business_name = None
        if o.user:
            customer = {
                "id": str(o.user.id),
                "name": o.user.name,
                "email": o.user.email,
                "phone": o.user.phone,
                "businessName": o.user.business_name,
                "business_name": o.user.business_name
            }
            customer_name = o.user.name
            business_name = o.user.business_name
        
        # Format order items
        items = []
        for item in o.order_items:
            product = item.product if hasattr(item, 'product') else None
            product_name = item.product_name if hasattr(item, 'product_name') else (product.name if product else "Product")
            product_image = item.product_image_url if hasattr(item, 'product_image_url') else None
            if not product_image and product:
                # Get primary image
                if hasattr(product, 'product_images') and product.product_images:
                    primary_image = next((img for img in product.product_images if img.is_primary), None)
                    if primary_image:
                        product_image = primary_image.image_url
                    elif product.product_images:
                        product_image = product.product_images[0].image_url
            
            items.append({
                "id": str(item.id),
                "productId": str(item.product_id) if item.product_id else None,
                "product": {
                    "id": str(product.id) if product else None,
                    "name": product_name,
                    "image": product_image,
                    "imageUrl": product_image
                } if product or product_name else None,
                "quantity": item.quantity,
                "price": float(item.price) if item.price else float(item.subtotal / item.quantity) if item.quantity > 0 else 0.0,
                "unitPrice": float(item.price) if item.price else float(item.subtotal / item.quantity) if item.quantity > 0 else 0.0,
                "total": float(item.subtotal),
                "subtotal": float(item.subtotal)
            })
        
        # Get payment info
        payment = None
        if o.payment_method or o.payment_status:
            payment = {
                "method": o.payment_method,
                "status": o.payment_status,
                "transactionId": o.payment_details.get("transaction_id") if isinstance(o.payment_details, dict) else None
            }
        
        # Format delivery address
        shipping_address = None
        if o.delivery_address and isinstance(o.delivery_address, dict):
            shipping_address = {
                "street": o.delivery_address.get("address_line1") or o.delivery_address.get("address") or "",
                "city": o.delivery_address.get("city") or "",
                "state": o.delivery_address.get("state") or "",
                "pincode": o.delivery_address.get("pincode") or ""
            }
        
        order_data = {
            "id": str(o.id),
            "orderId": o.order_number,
            "order_id": o.order_number,
            "orderNumber": o.order_number,
            "order_number": o.order_number,
            "customer": customer,
            "customerName": customer_name,
            "customer_name": customer_name,
            "businessName": business_name,
            "business_name": business_name,
            "items": items,
            "itemsCount": len(o.order_items),
            "items_count": len(o.order_items),
            "totalAmount": float(o.total_amount),
            "total_amount": float(o.total_amount),
            "total": float(o.total_amount),
            "amount": float(o.total_amount),
            "subtotal": float(o.subtotal),
            "tax": float(o.tax),
            "deliveryCharge": float(o.delivery_charge),
            "delivery_charge": float(o.delivery_charge),
            "discount": float(o.discount),
            "paymentMethod": o.payment_method,
            "payment_method": o.payment_method,
            "payment": payment,
            "status": o.status.value,
            "order_status": o.status.value,
            "createdAt": o.created_at.isoformat() if o.created_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "orderDate": o.created_at.isoformat() if o.created_at else None,
            "order_date": o.created_at.isoformat() if o.created_at else None,
            "deliveryDate": delivery_date,
            "delivery_date": delivery_date,
            "expectedDeliveryDate": delivery_date,
            "expected_delivery_date": delivery_date,
            "shippingAddress": shipping_address,
            "trackingNumber": o.tracking_number,
            "tracking_number": o.tracking_number,
            "notes": o.notes
        }
        order_list.append(order_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": order_list,
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
    # Convert UUID to string for query
    order_id_str = str(order_id)
    order = db.query(Order).options(
        joinedload(Order.user),
        joinedload(Order.order_items).joinedload(OrderItem.product).joinedload(Product.variants),
        joinedload(Order.order_items).joinedload(OrderItem.product).joinedload(Product.product_images),
        joinedload(Order.status_history)
    ).filter(Order.id == order_id_str).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Format order items with variants
    items = []
    for item in order.order_items:
        product = item.product if hasattr(item, 'product') else None
        product_name = item.product_name if hasattr(item, 'product_name') else (product.name if product else "Product")
        product_image = item.product_image_url if hasattr(item, 'product_image_url') else None
        
        # Get product image if not available
        if not product_image and product:
            if hasattr(product, 'product_images') and product.product_images:
                primary_image = next((img for img in product.product_images if img.is_primary), None)
                if primary_image:
                    product_image = primary_image.image_url
                elif product.product_images:
                    product_image = product.product_images[0].image_url
        
        # Get variant info
        variant = None
        if product and hasattr(product, 'variants') and product.variants:
            # Get first variant (or match by variant_id if stored in order_item)
            first_variant = product.variants[0]
            variant = {
                "id": str(first_variant.id),
                "weight": first_variant.weight,
                "setPieces": first_variant.set_pcs,
                "set_pieces": first_variant.set_pcs
            }
        
        unit_price = float(item.price) if item.price else (float(item.subtotal / item.quantity) if item.quantity > 0 else 0.0)
        
        items.append({
            "id": str(item.id),
            "productId": str(item.product_id) if item.product_id else None,
            "product": {
                "id": str(product.id) if product else None,
                "name": product_name,
                "image": product_image,
                "imageUrl": product_image,
                "sku": product.slug if product and hasattr(product, 'slug') else None
            } if product or product_name else None,
            "variant": variant,
            "quantity": item.quantity,
            "unitPrice": unit_price,
            "unit_price": unit_price,
            "total": float(item.subtotal),
            "subtotal": float(item.subtotal)
        })
    
    # Format status history
    status_history = []
    for history in order.status_history:
        status_history.append({
            "status": history.status.value,
            "timestamp": history.created_at.isoformat() if history.created_at else None,
            "notes": history.notes,
            "changedBy": str(history.changed_by) if history.changed_by else None,
            "createdAt": history.created_at.isoformat() if history.created_at else None
        })
    
    # Calculate delivery date
    delivery_date = None
    if order.status in [OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
        delivery_date = (order.created_at + timedelta(days=3)).isoformat() if order.created_at else None
    elif order.status == OrderStatus.DELIVERED or order.status == OrderStatus.COMPLETED:
        delivery_date = order.updated_at.isoformat() if order.updated_at else None
    
    # Format delivery address
    shipping_address = None
    if order.delivery_address and isinstance(order.delivery_address, dict):
        shipping_address = {
            "street": order.delivery_address.get("address_line1") or order.delivery_address.get("address") or "",
            "city": order.delivery_address.get("city") or "",
            "state": order.delivery_address.get("state") or "",
            "pincode": order.delivery_address.get("pincode") or ""
        }
    
    # Get payment info
    payment = None
    if order.payment_method or order.payment_status:
        payment = {
            "method": order.payment_method,
            "status": order.payment_status,
            "transactionId": order.payment_details.get("transaction_id") if isinstance(order.payment_details, dict) else None
        }
    
    order_data = {
        "id": str(order.id),
        "orderId": order.order_number,
        "order_id": order.order_number,
        "orderNumber": order.order_number,
        "order_number": order.order_number,
        "customer": {
            "id": str(order.user.id) if order.user else None,
            "name": order.user.name if order.user else "Unknown",
            "email": order.user.email if order.user else None,
            "phone": order.user.phone if order.user else None,
            "businessName": order.user.business_name if order.user else None,
            "business_name": order.user.business_name if order.user else None
        } if order.user else None,
        "customerName": order.user.name if order.user else "Unknown",
        "customer_name": order.user.name if order.user else "Unknown",
        "businessName": order.user.business_name if order.user else None,
        "business_name": order.user.business_name if order.user else None,
        "items": items,
        "itemsCount": len(order.order_items),
        "items_count": len(order.order_items),
        "subtotal": float(order.subtotal),
        "tax": float(order.tax),
        "deliveryCharge": float(order.delivery_charge),
        "delivery_charge": float(order.delivery_charge),
        "discount": float(order.discount),
        "totalAmount": float(order.total_amount),
        "total_amount": float(order.total_amount),
        "total": float(order.total_amount),
        "amount": float(order.total_amount),
        "paymentMethod": order.payment_method,
        "payment_method": order.payment_method,
        "payment": payment,
        "status": order.status.value,
        "order_status": order.status.value,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "orderDate": order.created_at.isoformat() if order.created_at else None,
        "order_date": order.created_at.isoformat() if order.created_at else None,
        "deliveryDate": delivery_date,
        "delivery_date": delivery_date,
        "expectedDeliveryDate": delivery_date,
        "expected_delivery_date": delivery_date,
        "shippingAddress": shipping_address,
        "deliveryAddress": shipping_address,
        "trackingNumber": order.tracking_number,
        "tracking_number": order.tracking_number,
        "notes": order.notes,
        "statusHistory": status_history,
        "status_history": status_history,
        "updatedAt": order.updated_at.isoformat() if order.updated_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=order_data,
        message="Order retrieved successfully"
    )


@router.put("/{order_id}/status", response_model=ResponseModel)
async def update_order_status(
    order_id: UUID,
    status_data: OrderStatusUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update order status"""
    order_id_str = str(order_id)
    order = db.query(Order).filter(Order.id == order_id_str).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Handle "canceled" -> "cancelled" mapping
    new_status = status_data.status
    if new_status.lower() == "canceled":
        new_status = "cancelled"
    
    try:
        order_status = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {new_status}. Valid values: {', '.join([s.value for s in OrderStatus])}"
        )
    
    # Validate status transition
    if order.status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        if order_status not in [OrderStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change status from {order.status.value} to {new_status}"
            )
    
    old_status = order.status
    order.status = order_status
    db.commit()
    
    # Create status history entry
    # Note: OrderStatusHistory uses UUID for order_id, but Order.id is String(36)
    # We need to handle this conversion
    from uuid import UUID as UUIDType
    try:
        order_uuid = UUIDType(order_id_str)
        status_history = OrderStatusHistory(
            order_id=order_uuid,
            status=order_status,
            changed_by=admin.id,
            notes=status_data.notes
        )
        db.add(status_history)
        db.commit()
    except (ValueError, AttributeError) as e:
        # If UUID conversion fails, log but don't fail
        # This can happen if order_id format doesn't match UUID
        print(f"Warning: Could not create status history entry: {e}")
    
    # Log activity
    try:
        entity_uuid = UUIDType(order_id_str)
    except (ValueError, AttributeError):
        entity_uuid = order_id_str
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="order_status_updated",
        entity_type="order",
        entity_id=entity_uuid,
        details={
            "old_status": old_status.value,
            "new_status": new_status,
            "notes": status_data.notes
        },
        request=request
    )
    
    # Refresh order to get updated status history
    db.refresh(order)
    
    return ResponseModel(
        success=True,
        data={
            "id": str(order.id),
            "status": order.status.value,
            "order_status": order.status.value
        },
        message="Order status updated successfully"
    )


@router.post("/{order_id}/cancel", response_model=ResponseModel)
async def cancel_order(
    order_id: UUID,
    cancel_data: OrderCancel,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    order_id_str = str(order_id)
    order = db.query(Order).filter(Order.id == order_id_str).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status in [OrderStatus.CANCELLED, OrderStatus.CANCELED]:
        raise HTTPException(status_code=400, detail="Order is already cancelled")
    
    if order.status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Cannot cancel a delivered or completed order")
    
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    order.cancelled_reason = cancel_data.reason
    db.commit()
    
    # Create status history
    from uuid import UUID as UUIDType
    try:
        order_uuid = UUIDType(order_id_str)
        status_history = OrderStatusHistory(
            order_id=order_uuid,
            status=OrderStatus.CANCELLED,
            changed_by=admin.id,
            notes=cancel_data.reason
        )
        db.add(status_history)
        db.commit()
    except (ValueError, AttributeError):
        # If UUID conversion fails, skip status history
        pass
    
    # Log activity
    try:
        entity_uuid = UUIDType(order_id_str)
    except:
        entity_uuid = order_id_str
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="order_cancelled",
        entity_type="order",
        entity_id=entity_uuid,
        details={"reason": cancel_data.reason},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Order cancelled successfully"
    )


@router.get("/{order_id}/invoice", response_model=ResponseModel)
async def get_order_invoice(
    order_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Get invoice for an order (returns invoice data as JSON)"""
    from app.api.v1.orders import get_invoice as get_user_invoice
    from app.api.deps import get_current_user
    
    # Get order to verify it exists
    order_id_str = str(order_id)
    order = db.query(Order).filter(Order.id == order_id_str).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get the user for the order (needed for invoice generation)
    user = order.user
    if not user:
        raise HTTPException(status_code=404, detail="Order user not found")
    
    # Create a mock current_user object for the invoice endpoint
    class MockUser:
        def __init__(self, user_obj):
            self.id = user_obj.id
            self.name = user_obj.name
            self.gst_number = user_obj.gst_number
            self.phone = user_obj.phone
    
    mock_user = MockUser(user)
    
    # Call the invoice generation logic
    # We'll reuse the logic from the user invoice endpoint
    seller = get_seller_info()
    
    # Get buyer information from delivery address
    delivery_address = order.delivery_address if isinstance(order.delivery_address, dict) else {}
    buyer_name = delivery_address.get("name") or user.name
    buyer_address_line1 = delivery_address.get("address_line1") or delivery_address.get("address") or ""
    buyer_address_line2 = delivery_address.get("address_line2") or delivery_address.get("landmark") or ""
    buyer_city = delivery_address.get("city") or ""
    buyer_state = delivery_address.get("state") or ""
    buyer_pincode = delivery_address.get("pincode") or ""
    buyer_gstin = delivery_address.get("gstin") or user.gst_number or ""
    buyer_phone = delivery_address.get("phone") or user.phone or ""
    
    buyer = {
        "name": buyer_name,
        "address_line1": buyer_address_line1,
        "address_line2": buyer_address_line2,
        "city": buyer_city,
        "state": buyer_state,
        "pincode": buyer_pincode,
        "gstin": buyer_gstin,
        "phone": buyer_phone
    }
    
    # Import invoice utilities
    from app.utils.invoice import (
        determine_supply_type,
        calculate_tax_rate,
        calculate_item_taxes,
        generate_invoice_number,
        calculate_savings,
        round_to_nearest_rupee
    )
    
    # Determine supply type
    supply_type = determine_supply_type(seller["state"], buyer_state)
    place_of_supply = buyer_state.upper() if buyer_state else seller["state"].upper()
    
    # Get order items with product details
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id_str).all()
    
    invoice_items = []
    tax_details_dict = {}
    total_taxable_amount = Decimal("0")
    total_sgst = Decimal("0")
    total_cgst = Decimal("0")
    total_igst = Decimal("0")
    
    for item in order_items:
        product = None
        if item.product_id:
            product = db.query(Product).options(
                joinedload(Product.variants),
                joinedload(Product.product_images)
            ).filter(Product.id == str(item.product_id)).first()
        
        # Get HSN code from product variant or default
        hsn_code = None
        variant_name = None
        if product:
            if hasattr(product, 'variants') and product.variants:
                first_variant = product.variants[0]
                hsn_code = first_variant.hsn_code if first_variant.hsn_code else None
                variant_name = f"{first_variant.set_pcs or product.unit} ({first_variant.weight or 'Set of 1'})" if first_variant.set_pcs or first_variant.weight else product.unit
            if not hsn_code:
                hsn_code = "07139090"
            if not variant_name:
                variant_name = product.unit or "EACH (Set of 1)"
        
        # Get prices
        mrp = Decimal(str(product.mrp)) if product and product.mrp else Decimal(str(item.price or 0)) * Decimal("1.2")
        selling_price = Decimal(str(item.price)) if item.price else (Decimal(str(product.selling_price)) if product and product.selling_price else Decimal("0"))
        quantity = Decimal(str(item.quantity))
        
        # Calculate discount
        unit_discount = mrp - selling_price if mrp > selling_price else Decimal("0")
        discount = unit_discount * quantity
        
        # Taxable amount
        taxable_amount = selling_price * quantity
        
        # Calculate tax rate
        tax_rate = calculate_tax_rate(hsn_code)
        
        # Calculate taxes
        taxes = calculate_item_taxes(taxable_amount, tax_rate, supply_type, seller["state"], buyer_state)
        
        # Add to totals
        total_taxable_amount += taxable_amount
        total_sgst += taxes["sgst"]
        total_cgst += taxes["cgst"]
        total_igst += taxes["igst"]
        
        # Group tax details
        if supply_type == "INTRASTATE":
            if taxes["sgst"] > 0:
                key = ("SGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["sgst"]
            if taxes["cgst"] > 0:
                key = ("CGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["cgst"]
        else:
            if taxes["igst"] > 0:
                key = ("IGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["igst"]
        
        # Item total
        item_total = taxable_amount + taxes["sgst"] + taxes["cgst"] + taxes["igst"]
        
        invoice_item = {
            "id": str(item.id),
            "product": {
                "id": str(product.id) if product else None,
                "name": product.name if product else (item.product_name if hasattr(item, 'product_name') else "Product"),
                "hsn": hsn_code,
                "variant": variant_name or (product.unit if product else "EACH (Set of 1)")
            },
            "quantity": float(quantity),
            "original_rate": float(mrp),
            "original_price": float(mrp),
            "mrp": float(mrp),
            "unit_discount": float(unit_discount),
            "discount": float(discount),
            "rate": float(selling_price),
            "selling_price": float(selling_price),
            "price": float(selling_price),
            "taxable_amount": float(taxable_amount),
            "sgst": float(taxes["sgst"]),
            "cgst": float(taxes["cgst"]),
            "tax_details": {
                "sgst": float(taxes["sgst"]),
                "cgst": float(taxes["cgst"]),
                "igst": float(taxes["igst"]),
                "rate": tax_rate
            },
            "total_amount": float(item_total)
        }
        invoice_items.append(invoice_item)
    
    # Convert tax_details_dict to list
    tax_details_list = []
    for (tax_type, rate), amounts in tax_details_dict.items():
        tax_details_list.append({
            "tax_type": tax_type,
            "name": tax_type,
            "taxable_amount": float(amounts["taxable_amount"]),
            "rate": rate,
            "tax_amount": float(amounts["tax_amount"])
        })
    tax_details_list.sort(key=lambda x: (x["tax_type"], x["rate"]))
    
    # Calculate totals
    subtotal = total_taxable_amount
    total_tax = total_sgst + total_cgst + total_igst
    delivery_charge = Decimal(str(order.delivery_charge)) if order.delivery_charge else Decimal("0")
    
    # Calculate grand total
    grand_total = subtotal + total_tax + delivery_charge
    
    # Round off
    rounded_total, round_off = round_to_nearest_rupee(grand_total)
    
    # Calculate savings
    savings = calculate_savings(invoice_items)
    
    # Generate invoice number
    invoice_number = generate_invoice_number(str(order.id), order.order_number)
    
    # Format invoice date and time
    invoice_date = order.created_at if order.created_at else datetime.utcnow()
    invoice_time = invoice_date.strftime("%I:%M %p") if invoice_date else "11:00 AM"
    
    # Build invoice data
    invoice_data = {
        "invoice_number": invoice_number,
        "reference_number": invoice_number,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "shipment_number": order.tracking_number or "",
        "invoice_date": invoice_date.isoformat() if invoice_date else datetime.utcnow().isoformat(),
        "created_at": invoice_date.isoformat() if invoice_date else datetime.utcnow().isoformat(),
        "time": invoice_time,
        "place_of_supply": place_of_supply,
        "supply_type": supply_type,
        "page_number": "1/1",
        "seller": seller,
        "buyer": buyer,
        "items": invoice_items,
        "tax_details": tax_details_list,
        "subtotal": float(subtotal),
        "taxable_amount": float(subtotal),
        "delivery_charge": float(delivery_charge),
        "total_tax": float(total_tax),
        "round_off": float(round_off),
        "total": float(rounded_total),
        "grand_total": float(rounded_total),
        "paid_amount": float(rounded_total) if order.payment_status == "paid" else float(0),
        "balance": float(0) if order.payment_status == "paid" else float(rounded_total),
        "savings": float(savings),
        "tax_payable_reverse_charge": False,
        "terms": "This transaction/sales is subject to TDS U/s 194-O hence TDS U/s 194Q is not applicable. This is a computer-generated invoice. For any issues, please contact Customer Care team.",
        "notes": order.notes or "Thanks for doing business with us!"
    }
    
    # Return as JSON (PDF generation can be added later)
    return ResponseModel(
        success=True,
        data=invoice_data,
        message="Invoice retrieved successfully"
    )

