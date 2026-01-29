from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import random
import string


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DELY{timestamp}{random_str}"


def calculate_order_totals(items: list, db: Session) -> dict:
    """Calculate order totals"""
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    
    for item in items:
        # `products.id` is String(36) in DB; request schemas may provide UUID objects
        product = db.query(Product).filter(Product.id == str(item["product_id"])).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item['product_id']} not found"
            )
        
        qty = int(item["quantity"])

        # Prefer new fields; fall back to legacy fields for older records.
        stock_available = (
            int(product.stock_quantity)
            if getattr(product, "stock_quantity", None) is not None
            else int(getattr(product, "stock", 0) or 0)
        )
        min_order_qty = (
            int(product.min_order_quantity)
            if getattr(product, "min_order_quantity", None) is not None
            else int(getattr(product, "min_order", 1) or 1)
        )

        selling_price = getattr(product, "selling_price", None) or getattr(product, "price", None)
        mrp = getattr(product, "mrp", None) or getattr(product, "original_price", None) or selling_price

        if stock_available < qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}"
            )
        
        if qty < min_order_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum order quantity for {product.name} is {product.min_order}"
            )
        
        # Numeric columns are usually Decimal already; keep math in Decimal.
        item_subtotal = selling_price * qty
        item_discount = (mrp - selling_price) * qty if mrp and selling_price else Decimal("0.00")
        subtotal += item_subtotal
        discount += item_discount
    
    # Calculate delivery charge
    delivery_charge = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
    
    # Calculate tax
    tax = (subtotal - discount) * Decimal('0.18')
    
    # Calculate total
    total = subtotal - discount + delivery_charge + tax
    
    return {
        "subtotal": subtotal,
        "discount": discount,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "total": total
    }

