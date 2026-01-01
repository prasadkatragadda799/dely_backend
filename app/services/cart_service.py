from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.cart import Cart
from app.models.product import Product
from app.models.user import User
from uuid import UUID
from decimal import Decimal


def get_cart_summary(db: Session, user_id: UUID) -> dict:
    """Calculate cart summary"""
    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            item_subtotal = product.price * item.quantity
            item_discount = (product.original_price - product.price) * item.quantity
            subtotal += item_subtotal
            discount += item_discount
    
    # Calculate delivery charge (free above 1000, else 50)
    delivery_charge = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
    
    # Calculate tax (18% GST)
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

