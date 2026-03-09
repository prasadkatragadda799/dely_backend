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


def get_cart_summary_for_division(db: Session, user_id: str, product_ids: list) -> dict:
    """Calculate cart summary for a subset of cart items (e.g. one division)."""
    if not product_ids:
        return {
            "subtotal": 0.0,
            "discount": 0.0,
            "delivery_charge": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "item_count": 0
        }
    cart_items = db.query(Cart).filter(
        Cart.user_id == str(user_id),
        Cart.product_id.in_(product_ids)
    ).all()
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    for item in cart_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            price = product.selling_price if product.selling_price else (product.price if hasattr(product, 'price') and product.price else Decimal('0.00'))
            mrp = product.mrp if product.mrp else (product.original_price if hasattr(product, 'original_price') and product.original_price else price)
            subtotal += price * item.quantity
            discount += (mrp - price) * item.quantity
    delivery_charge = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
    tax = subtotal * Decimal('0.18')
    total = subtotal + delivery_charge + tax
    item_count = sum(item.quantity for item in cart_items)
    return {
        "subtotal": float(subtotal),
        "discount": float(discount),
        "delivery_charge": float(delivery_charge),
        "tax": float(tax),
        "total": float(total),
        "item_count": item_count
    }

