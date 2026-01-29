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
        
        if product.stock < item['quantity']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}"
            )
        
        if item['quantity'] < product.min_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum order quantity for {product.name} is {product.min_order}"
            )
        
        item_subtotal = product.price * item['quantity']
        item_discount = (product.original_price - product.price) * item['quantity']
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

