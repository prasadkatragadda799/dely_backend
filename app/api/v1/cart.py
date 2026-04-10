from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.v1.products import _resolve_division_id
from app.api.deps import get_current_user
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse, CartSummary
from app.schemas.common import ResponseModel
from app.models.cart import Cart
from app.models.product import Product
from app.services.cart_service import summarize_cart_lines
from app.utils.product_pricing import (
    assert_tier_allowed,
    customer_price_with_commission,
    discount_percent,
    normalize_price_tier,
    tier_mrp,
)
from uuid import UUID
from decimal import Decimal
from typing import Optional

router = APIRouter()


def _cart_line_product_dict(product: Product, price_tier: str = "unit") -> dict:
    """Cart line product snapshot; price matches the selected tier (incl. commission)."""
    tier = normalize_price_tier(price_tier)
    sell_dec = customer_price_with_commission(product, tier)
    mrp_dec = tier_mrp(product, tier)
    price = float(sell_dec)
    original = float(mrp_dec) if mrp_dec else price
    variant_set = None
    if getattr(product, "variants", None):
        for v in product.variants:
            sp = getattr(v, "set_pcs", None)
            if sp is not None and str(sp).strip():
                variant_set = str(sp).strip()
                break
    d = {
        "id": product.id,
        "name": product.name,
        "brand": product.brand_rel.name if product.brand_rel else (
            product.brand if hasattr(product, "brand") else ""
        ),
        "price": price,
        "original_price": original,
        "discount": discount_percent(mrp_dec, sell_dec),
        "images": [],
        "rating": float(product.rating) if product.rating else 0.0,
        "is_available": product.is_available,
        "is_featured": product.is_featured,
        "unit": product.unit or "piece",
        "piecesPerSet": int(product.pieces_per_set) if product.pieces_per_set is not None else 1,
        "minOrderQuantity": int(product.min_order_quantity)
        if getattr(product, "min_order_quantity", None) is not None
        else int(getattr(product, "min_order", None) or 1),
        "divisionId": str(product.division_id) if getattr(product, "division_id", None) else None,
        "divisionSlug": (
            str(product.division.slug).strip().lower()
            if getattr(product, "division", None) is not None
            and getattr(product.division, "slug", None) is not None
            else None
        ),
        "categorySlug": (
            str(product.category.slug).strip().lower()
            if getattr(product, "category", None) is not None
            and getattr(product.category, "slug", None) is not None
            else None
        ),
    }
    if variant_set:
        d["variantSetPieces"] = variant_set
    if product.product_images:
        d["images"] = [
            img.image_url
            for img in sorted(product.product_images, key=lambda x: x.display_order)
        ]
    elif hasattr(product, "images") and product.images and isinstance(product.images, list):
        d["images"] = product.images
    return d


@router.get("", response_model=ResponseModel)
def get_cart(
    division_slug: Optional[str] = Query(
        None,
        description="Filter cart lines: 'fmcg'/'default'/'grocery' = grocery (NULL or default division id); "
        "'kitchen'/'home'/'homeKitchen' = kitchen/home division. Omit for all items.",
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's cart. When division_slug is set, return only lines for that vertical (mobile tabs)."""
    cart_items = db.query(Cart).filter(Cart.user_id == str(current_user.id)).all()
    division_filtered = False

    if division_slug:
        division_filtered = True
        slug = division_slug.strip().lower()
        if slug in ("fmcg", "default", "grocery"):
            default_id = _resolve_division_id(db, "default")
            if default_id:
                cart_items = [
                    c
                    for c in cart_items
                    if c.division_id is None or str(c.division_id) == default_id
                ]
            else:
                cart_items = [c for c in cart_items if c.division_id is None]
        elif slug in ("homekitchen", "kitchen", "home"):
            div_id = _resolve_division_id(db, "kitchen") or _resolve_division_id(db, "home")
            if div_id is not None:
                cart_items = [c for c in cart_items if c.division_id == div_id]
            else:
                cart_items = []
        else:
            div_id = _resolve_division_id(db, division_slug)
            if div_id is not None:
                cart_items = [c for c in cart_items if c.division_id == div_id]
            else:
                cart_items = []

    items = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            tier = getattr(item, "price_option_key", None) or "unit"
            sell_dec = customer_price_with_commission(product, tier)
            subtotal = sell_dec * item.quantity
            product_data = _cart_line_product_dict(product, tier)
            items.append({
                "id": str(item.id),
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "price_option_key": tier,
                "product": product_data,
                "subtotal": float(subtotal),
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            })

    summary_data = summarize_cart_lines(db, cart_items)
    summary = CartSummary(**summary_data)

    return ResponseModel(
        success=True,
        data={
            "items": items,
            "summary": summary.dict()
        }
    )


@router.post("", response_model=ResponseModel)
def add_to_cart(
    item_data: CartItemAdd,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add item to cart. Items may be from any division; each line stores its product's division."""
    product = db.query(Product).filter(Product.id == str(item_data.product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.is_available:
        raise HTTPException(status_code=400, detail="Product is not available")

    tier = normalize_price_tier(getattr(item_data, "price_option_key", None))
    assert_tier_allowed(product, tier)

    stock = product.stock_quantity if product.stock_quantity else (product.stock if hasattr(product, 'stock') and product.stock else 0)
    if stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    min_order = product.min_order_quantity if product.min_order_quantity else (product.min_order if hasattr(product, 'min_order') and product.min_order else 1)

    product_division_id = str(product.division_id) if product.division_id else None

    existing_item = db.query(Cart).filter(
        Cart.user_id == str(current_user.id),
        Cart.product_id == str(item_data.product_id),
        Cart.price_option_key == tier,
    ).first()

    if existing_item:
        if item_data.quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        new_line_qty = existing_item.quantity + item_data.quantity
        if new_line_qty < min_order:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum order quantity is {min_order}"
            )
        existing_item.quantity += item_data.quantity
        db.commit()
        db.refresh(existing_item)
    else:
        if item_data.quantity < min_order:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum order quantity is {min_order}"
            )
        cart_item = Cart(
            user_id=str(current_user.id),
            product_id=str(item_data.product_id),
            division_id=product_division_id,
            price_option_key=tier,
            quantity=item_data.quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        existing_item = cart_item

    # Return full cart after adding item (matching requirements)
    cart_items = db.query(Cart).filter(Cart.user_id == str(current_user.id)).all()
    items = []
    for cart_item in cart_items:
        prod = db.query(Product).filter(Product.id == str(cart_item.product_id)).first()
        if prod:
            ctier = getattr(cart_item, "price_option_key", None) or "unit"
            sell_dec = customer_price_with_commission(prod, ctier)
            subtotal_val = sell_dec * cart_item.quantity
            prod_dict = _cart_line_product_dict(prod, ctier)
            items.append({
                "id": str(cart_item.id),
                "product_id": str(cart_item.product_id),
                "quantity": cart_item.quantity,
                "price_option_key": ctier,
                "product": prod_dict,
                "subtotal": float(subtotal_val),
                "created_at": cart_item.created_at.isoformat() if cart_item.created_at else None,
                "updated_at": cart_item.updated_at.isoformat() if cart_item.updated_at else None
            })

    summary_data = summarize_cart_lines(db, cart_items)
    summary = CartSummary(**summary_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": items,
            "summary": summary.dict()
        },
        message="Item added to cart"
    )


def _clear_cart_for_user(db: Session, user_id: str) -> None:
    db.query(Cart).filter(Cart.user_id == str(user_id)).delete()
    db.commit()


@router.delete("", response_model=ResponseModel)
def clear_cart_root(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Clear all items from cart (preferred endpoint: DELETE /api/v1/cart)"""
    _clear_cart_for_user(db, str(current_user.id))
    return ResponseModel(success=True, message="Cart cleared")


@router.delete("/clear", response_model=ResponseModel)
def clear_cart(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Clear all items from cart (legacy alias: DELETE /api/v1/cart/clear)"""
    _clear_cart_for_user(db, str(current_user.id))
    return ResponseModel(success=True, message="Cart cleared")


@router.put("/{cart_item_id}", response_model=ResponseModel)
def update_cart_item(
    cart_item_id: UUID,
    item_data: CartItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    cart_item = db.query(Cart).filter(
        Cart.id == str(cart_item_id),
        Cart.user_id == str(current_user.id)
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    product = db.query(Product).filter(Product.id == str(cart_item.product_id)).first()
    stock = product.stock_quantity if product.stock_quantity else (product.stock if hasattr(product, 'stock') and product.stock else 0)
    if stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    min_order = product.min_order_quantity if product.min_order_quantity else (product.min_order if hasattr(product, 'min_order') and product.min_order else 1)
    if item_data.quantity < min_order:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order quantity is {min_order}"
        )
    
    cart_item.quantity = item_data.quantity
    db.commit()
    
    return ResponseModel(success=True, message="Cart item updated")


@router.delete("/{cart_item_id}", response_model=ResponseModel)
def remove_from_cart(
    cart_item_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    cart_item = db.query(Cart).filter(
        Cart.id == str(cart_item_id),
        Cart.user_id == str(current_user.id)
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    
    return ResponseModel(success=True, message="Item removed from cart")
