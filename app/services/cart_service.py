from sqlalchemy.orm import Session
from app.models.cart import Cart
from app.models.product import Product
from decimal import Decimal

from app.utils.product_pricing import (
    customer_price_with_commission,
    tier_mrp,
)


def summarize_cart_lines(db: Session, cart_items: list) -> dict:
    """Subtotal/discount/tax from cart ORM rows (respects price_option_key per line)."""
    subtotal = Decimal("0.00")
    discount = Decimal("0.00")

    for item in cart_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if not product:
            continue
        tier = getattr(item, "price_option_key", None) or "unit"
        price = customer_price_with_commission(product, tier)
        mrp = tier_mrp(product, tier)
        item_subtotal = price * item.quantity
        item_discount = (mrp - price) * item.quantity if mrp and price else Decimal("0.00")
        subtotal += item_subtotal
        discount += item_discount

    delivery_charge = Decimal("0.00") if subtotal >= 1000 else Decimal("50.00")
    tax = subtotal * Decimal("0.18")
    total = subtotal + delivery_charge + tax
    item_count = sum(item.quantity for item in cart_items)

    return {
        "subtotal": float(subtotal),
        "discount": float(discount),
        "delivery_charge": float(delivery_charge),
        "tax": float(tax),
        "total": float(total),
        "item_count": item_count,
    }


def get_cart_summary(db: Session, user_id: str) -> dict:
    cart_items = db.query(Cart).filter(Cart.user_id == str(user_id)).all()
    return summarize_cart_lines(db, cart_items)


def get_cart_summary_for_division(db: Session, user_id: str, product_ids: list) -> dict:
    """Deprecated path: prefer passing filtered cart rows. Kept for callers that only have product ids."""
    if not product_ids:
        return {
            "subtotal": 0.0,
            "discount": 0.0,
            "delivery_charge": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "item_count": 0,
        }
    cart_items = db.query(Cart).filter(
        Cart.user_id == str(user_id),
        Cart.product_id.in_(product_ids),
    ).all()
    return summarize_cart_lines(db, cart_items)

