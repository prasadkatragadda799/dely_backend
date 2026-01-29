from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse, CartSummary
from app.schemas.common import ResponseModel
from app.models.cart import Cart
from app.models.product import Product
from app.services.cart_service import get_cart_summary
from uuid import UUID
from decimal import Decimal

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_cart(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's cart"""
    cart_items = db.query(Cart).filter(Cart.user_id == str(current_user.id)).all()
    
    items = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == str(item.product_id)).first()
        if product:
            # Use selling_price (or fallback to price if legacy field exists)
            price = float(product.selling_price) if product.selling_price else (float(product.price) if hasattr(product, 'price') and product.price else 0.0)
            subtotal = Decimal(str(price)) * item.quantity
            
            # Format product data manually to avoid schema validation issues
            product_data = {
                "id": product.id,
                "name": product.name,
                "brand": product.brand_rel.name if product.brand_rel else (product.brand if hasattr(product, 'brand') else ""),
                "price": price,
                "original_price": float(product.mrp) if product.mrp else price,
                "discount": 0.0,
                "images": [],
                "rating": float(product.rating) if product.rating else 0.0,
                "is_available": product.is_available,
                "is_featured": product.is_featured
            }
            
            # Add images
            if product.product_images:
                product_data["images"] = [img.image_url for img in sorted(product.product_images, key=lambda x: x.display_order)]
            elif hasattr(product, 'images') and product.images:
                if isinstance(product.images, list):
                    product_data["images"] = product.images
            
            # Calculate discount
            if product.mrp and product.selling_price and product.mrp > 0:
                product_data["discount"] = round(float(((product.mrp - product.selling_price) / product.mrp) * 100), 2)
            
            items.append({
                "id": str(item.id),
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "product": product_data,
                "subtotal": float(subtotal),
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            })
    
    summary_data = get_cart_summary(db, current_user.id)
    summary = CartSummary(**summary_data)
    
    # Return cart with proper structure
    return ResponseModel(
        success=True,
        data={
            "items": items,  # Already a list of dicts
            "summary": summary.dict()
        }
    )


@router.post("", response_model=ResponseModel)
def add_to_cart(
    item_data: CartItemAdd,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    product = db.query(Product).filter(Product.id == str(item_data.product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=400, detail="Product is not available")
    
    stock = product.stock_quantity if product.stock_quantity else (product.stock if hasattr(product, 'stock') and product.stock else 0)
    if stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    min_order = product.min_order_quantity if product.min_order_quantity else (product.min_order if hasattr(product, 'min_order') and product.min_order else 1)
    if item_data.quantity < min_order:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order quantity is {min_order}"
        )
    
    # Check if item already in cart
    existing_item = db.query(Cart).filter(
        Cart.user_id == str(current_user.id),
        Cart.product_id == str(item_data.product_id)
    ).first()
    
    if existing_item:
        existing_item.quantity += item_data.quantity
        db.commit()
        db.refresh(existing_item)
    else:
        cart_item = Cart(
            user_id=str(current_user.id),
            product_id=str(item_data.product_id),
            quantity=item_data.quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        existing_item = cart_item
    
    product_data = db.query(Product).filter(Product.id == str(item_data.product_id)).first()
    price = float(product_data.selling_price) if product_data.selling_price else (float(product_data.price) if hasattr(product_data, 'price') and product_data.price else 0.0)
    subtotal = Decimal(str(price)) * existing_item.quantity
    
    # Format product data
    product_dict = {
        "id": product_data.id,
        "name": product_data.name,
        "brand": product_data.brand_rel.name if product_data.brand_rel else (product_data.brand if hasattr(product_data, 'brand') else ""),
        "price": price,
        "original_price": float(product_data.mrp) if product_data.mrp else price,
        "discount": 0.0,
        "images": [],
        "rating": float(product_data.rating) if product_data.rating else 0.0,
        "is_available": product_data.is_available,
        "is_featured": product_data.is_featured
    }
    
    if product_data.product_images:
        product_dict["images"] = [img.image_url for img in sorted(product_data.product_images, key=lambda x: x.display_order)]
    elif hasattr(product_data, 'images') and product_data.images:
        if isinstance(product_data.images, list):
            product_dict["images"] = product_data.images
    
    if product_data.mrp and product_data.selling_price and product_data.mrp > 0:
        product_dict["discount"] = round(float(((product_data.mrp - product_data.selling_price) / product_data.mrp) * 100), 2)
    
    # Return full cart after adding item (matching requirements)
    cart_items = db.query(Cart).filter(Cart.user_id == str(current_user.id)).all()
    items = []
    for cart_item in cart_items:
        prod = db.query(Product).filter(Product.id == str(cart_item.product_id)).first()
        if prod:
            price = float(prod.selling_price) if prod.selling_price else (float(prod.price) if hasattr(prod, 'price') and prod.price else 0.0)
            subtotal_val = Decimal(str(price)) * cart_item.quantity
            
            prod_dict = {
                "id": prod.id,
                "name": prod.name,
                "brand": prod.brand_rel.name if prod.brand_rel else (prod.brand if hasattr(prod, 'brand') else ""),
                "price": price,
                "original_price": float(prod.mrp) if prod.mrp else price,
                "discount": 0.0,
                "images": [],
                "rating": float(prod.rating) if prod.rating else 0.0,
                "is_available": prod.is_available,
                "is_featured": prod.is_featured
            }
            
            if prod.product_images:
                prod_dict["images"] = [{"url": img.image_url, "is_primary": img.is_primary} for img in sorted(prod.product_images, key=lambda x: x.display_order)]
            elif hasattr(prod, 'images') and prod.images:
                if isinstance(prod.images, list):
                    prod_dict["images"] = [{"url": img, "is_primary": idx == 0} for idx, img in enumerate(prod.images)]
            
            if prod.mrp and prod.selling_price and prod.mrp > 0:
                prod_dict["discount"] = round(float(((prod.mrp - prod.selling_price) / prod.mrp) * 100), 2)
            
            items.append({
                "id": str(cart_item.id),
                "product_id": str(cart_item.product_id),
                "quantity": cart_item.quantity,
                "product": prod_dict,
                "subtotal": float(subtotal_val),
                "created_at": cart_item.created_at.isoformat() if cart_item.created_at else None,
                "updated_at": cart_item.updated_at.isoformat() if cart_item.updated_at else None
            })
    
    summary_data = get_cart_summary(db, current_user.id)
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
