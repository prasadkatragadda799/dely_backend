from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.utils.product_pricing import (
    assert_tier_allowed,
    customer_price_with_commission,
    normalize_price_tier,
    tier_mrp,
    variant_customer_price,
    variant_mrp,
)
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional
import re
import random
import string


def variant_pieces_per_unit(variant) -> int:
    """Return how many stock-pieces one ordered unit of this variant consumes.

    set_pcs is a free-form admin string like '1*6', '1*12', '6', '12'.
    We extract all digit groups and multiply them (1×6=6, 1×12=12).
    Falls back to 1 so a missing/unknown format is safe.
    """
    raw = getattr(variant, 'set_pcs', None)
    if not raw:
        return 1
    nums = [int(n) for n in re.findall(r'\d+', str(raw))]
    if not nums:
        return 1
    result = 1
    for n in nums:
        result *= n
    return max(1, result)


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

        variant = None
        if item.get("variant_id"):
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == str(item["variant_id"]),
                ProductVariant.product_id == str(item["product_id"]),
            ).first()
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Variant {item['variant_id']} not found for product {item['product_id']}",
                )

        if variant is not None:
            selling_price = variant_customer_price(product, variant)
            mrp = variant_mrp(variant)
        else:
            tier = normalize_price_tier(item.get("price_option_key"))
            assert_tier_allowed(product, tier)
            selling_price = customer_price_with_commission(product, tier)
            mrp = tier_mrp(product, tier)

        if variant is not None:
            pieces_needed = qty * variant_pieces_per_unit(variant)
        else:
            _tier = normalize_price_tier(item.get("price_option_key"))
            _pps = max(1, int(getattr(product, 'pieces_per_set', 1) or 1))
            pieces_needed = qty * (_pps if _tier == 'set' else 1)

        if stock_available < pieces_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}"
            )
        
        if qty < min_order_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum order quantity for {product.name} is {min_order_qty}"
            )
        
        # Numeric columns are usually Decimal already; keep math in Decimal.
        item_subtotal = selling_price * qty
        item_discount = (mrp - selling_price) * qty if mrp and selling_price else Decimal("0.00")
        subtotal += item_subtotal
        discount += item_discount
    
    # Calculate delivery charge
    delivery_charge = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
    
    # Selling prices are GST-inclusive (tax is already embedded in the price the
    # customer sees). Extract the GST portion for invoice reporting — do NOT add
    # it again on top, which would inflate the total by 18% incorrectly.
    # tax = subtotal × rate / (1 + rate)  →  the share of tax already inside subtotal
    tax = subtotal * Decimal('0.18') / Decimal('1.18')

    # Total payable = selling-price sum + delivery. Tax is already inside subtotal.
    total = subtotal + delivery_charge
    
    return {
        "subtotal": subtotal,
        "discount": discount,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "total": total
    }

