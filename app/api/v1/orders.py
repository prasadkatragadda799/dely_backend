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
from app.utils.invoice import (
    get_seller_info,
    calculate_tax_rate,
    determine_supply_type,
    calculate_item_taxes,
    generate_invoice_number,
    calculate_savings,
    round_to_nearest_rupee
)
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

router = APIRouter()


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
    
    # Calculate totals
    items_data = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_data.items]
    totals = calculate_order_totals(items_data, db)
    
    # Create order
    order = Order(
        order_number=generate_order_number(),
        user_id=str(current_user.id),
        status=OrderStatus.PENDING,
        delivery_address=delivery_address,
        payment_method=order_data.payment_method,
        payment_details=order_data.payment_details,
        subtotal=totals["subtotal"],
        discount=totals["discount"],
        delivery_charge=totals["delivery_charge"],
        tax=totals["tax"],
        # DB schema requires `total` (NOT NULL). Keep `total_amount` in sync if present.
        total=totals["total"],
        total_amount=totals["total"],
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


@router.get("/{order_id}/invoice", response_model=ResponseModel)
def get_invoice(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invoice for an order"""
    # Get order
    order = db.query(Order).filter(
        Order.id == str(order_id),
        Order.user_id == str(current_user.id)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get seller information
    seller = get_seller_info()
    
    # Get buyer information from delivery address
    delivery_address = order.delivery_address if isinstance(order.delivery_address, dict) else {}
    buyer_name = delivery_address.get("name") or current_user.name
    buyer_address_line1 = delivery_address.get("address_line1") or delivery_address.get("address") or ""
    buyer_address_line2 = delivery_address.get("address_line2") or delivery_address.get("landmark") or ""
    buyer_city = delivery_address.get("city") or ""
    buyer_state = delivery_address.get("state") or ""
    buyer_pincode = delivery_address.get("pincode") or ""
    buyer_gstin = delivery_address.get("gstin") or current_user.gst_number or ""
    buyer_phone = delivery_address.get("phone") or current_user.phone or ""
    
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
    
    # Determine supply type
    supply_type = determine_supply_type(seller["state"], buyer_state)
    place_of_supply = buyer_state.upper() if buyer_state else seller["state"].upper()
    
    # Get order items with product details
    order_items = db.query(OrderItem).filter(OrderItem.order_id == str(order.id)).all()
    
    invoice_items = []
    # Use dict to group tax details by tax_type and rate
    tax_details_dict = {}  # Key: (tax_type, rate), Value: {"taxable_amount": sum, "tax_amount": sum}
    total_taxable_amount = Decimal("0")
    total_sgst = Decimal("0")
    total_cgst = Decimal("0")
    total_igst = Decimal("0")
    
    for item in order_items:
        product = None
        if item.product_id:
            # Load product with variants relationship
            from sqlalchemy.orm import joinedload
            product = db.query(Product).options(joinedload(Product.variants)).filter(Product.id == str(item.product_id)).first()
        
        # Get HSN code from product variant or default
        hsn_code = None
        variant_name = None
        if product:
            # Try to get HSN from variants
            if hasattr(product, 'variants') and product.variants:
                # Get first variant's HSN code
                first_variant = product.variants[0]
                hsn_code = first_variant.hsn_code if first_variant.hsn_code else None
                variant_name = f"{first_variant.set_pcs or product.unit} ({first_variant.weight or 'Set of 1'})" if first_variant.set_pcs or first_variant.weight else product.unit
            # If no variant or no HSN in variant, use default
            if not hsn_code:
                hsn_code = "07139090"  # Default HSN code
            if not variant_name:
                variant_name = product.unit or "EACH (Set of 1)"
        
        # Get prices
        mrp = Decimal(str(product.mrp)) if product and product.mrp else Decimal(str(item.price or 0)) * Decimal("1.2")  # Estimate MRP if not available
        selling_price = Decimal(str(item.price)) if item.price else (Decimal(str(product.selling_price)) if product and product.selling_price else Decimal("0"))
        quantity = Decimal(str(item.quantity))
        
        # Calculate discount
        unit_discount = mrp - selling_price if mrp > selling_price else Decimal("0")
        discount = unit_discount * quantity
        
        # Taxable amount (before tax)
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
        
        # Group tax details by tax_type and rate
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
        
        # Item total (including tax)
        item_total = taxable_amount + taxes["sgst"] + taxes["cgst"] + taxes["igst"]
        
        invoice_item = {
            "id": str(item.id),
            "product": {
                "id": str(product.id) if product else None,
                "name": product.name if product else (item.product_name or "Product"),
                "hsn": hsn_code,
                "variant": variant_name or product.unit if product else "EACH (Set of 1)"
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
    
    # Calculate totals
    subtotal = total_taxable_amount
    total_tax = total_sgst + total_cgst + total_igst
    delivery_charge = Decimal(str(order.delivery_charge)) if order.delivery_charge else Decimal("0")
    
    # Calculate grand total
    grand_total = subtotal + total_tax + delivery_charge
    
    # Round off
    rounded_total, round_off = round_to_nearest_rupee(grand_total)
    
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
    
    # Sort tax details by tax_type and rate
    tax_details_list.sort(key=lambda x: (x["tax_type"], x["rate"]))
    
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
    
    return ResponseModel(
        success=True,
        data=invoice_data,
        message="Invoice fetched successfully"
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

