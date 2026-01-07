from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.cart import Cart
from app.models.product import Product
from app.models.user import User
from uuid import UUID
from decimal import Decimal


def get_cart_summary(db: Session, user_id: str) -> dict:
    """Calculate cart summary"""
    cart_items = db.query(Cart).filter(Cart.user_id == str(user_id)).all()
    
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    
    for item in cart_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            # Use selling_price (or fallback to legacy price field)
            price = product.selling_price if product.selling_price else (product.price if hasattr(product, 'price') and product.price else Decimal('0.00'))
            mrp = product.mrp if product.mrp else (product.original_price if hasattr(product, 'original_price') and product.original_price else price)
            
            item_subtotal = price * item.quantity
            item_discount = (mrp - price) * item.quantity
            subtotal += item_subtotal
            discount += item_discount
    
    # Calculate delivery charge (free above 1000, else 50)
    delivery_charge = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
    
    # Calculate tax (18% GST on subtotal, since selling_price is already discounted)
    tax = subtotal * Decimal('0.18')
    
    # Calculate total
    # Note: selling_price is already discounted, so total = subtotal + delivery + tax
    # We don't subtract discount again since it's already applied to selling_price
    total = subtotal + delivery_charge + tax
    
    # Count total items
    item_count = sum(item.quantity for item in cart_items)
    
    # Convert Decimal to float for JSON serialization
    return {
        "subtotal": float(subtotal),
        "discount": float(discount),
        "delivery_charge": float(delivery_charge),
        "tax": float(tax),
        "total": float(total),
        "item_count": item_count
    }

