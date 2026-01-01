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
    cart_items = db.query(Cart).filter(Cart.user_id == current_user.id).all()
    
    items = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            from app.schemas.product import ProductListResponse
            subtotal = product.price * item.quantity
            items.append(CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                product=ProductListResponse.model_validate(product),
                subtotal=subtotal,
                created_at=item.created_at,
                updated_at=item.updated_at
            ))
    
    summary_data = get_cart_summary(db, current_user.id)
    summary = CartSummary(**summary_data)
    
    return ResponseModel(
        success=True,
        data=CartResponse(items=items, summary=summary)
    )


@router.post("/add", response_model=ResponseModel)
def add_to_cart(
    item_data: CartItemAdd,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    product = db.query(Product).filter(Product.id == item_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=400, detail="Product is not available")
    
    if product.stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    if item_data.quantity < product.min_order:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order quantity is {product.min_order}"
        )
    
    # Check if item already in cart
    existing_item = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.product_id == item_data.product_id
    ).first()
    
    if existing_item:
        existing_item.quantity += item_data.quantity
        db.commit()
        db.refresh(existing_item)
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        existing_item = cart_item
    
    product_data = db.query(Product).filter(Product.id == item_data.product_id).first()
    from app.schemas.product import ProductListResponse
    subtotal = product_data.price * existing_item.quantity
    
    return ResponseModel(
        success=True,
        data=CartItemResponse(
            id=existing_item.id,
            product_id=existing_item.product_id,
            quantity=existing_item.quantity,
            product=ProductListResponse.model_validate(product_data),
            subtotal=subtotal,
            created_at=existing_item.created_at,
            updated_at=existing_item.updated_at
        ),
        message="Item added to cart"
    )


@router.put("/update/{cart_item_id}", response_model=ResponseModel)
def update_cart_item(
    cart_item_id: UUID,
    item_data: CartItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if product.stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    if item_data.quantity < product.min_order:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order quantity is {product.min_order}"
        )
    
    cart_item.quantity = item_data.quantity
    db.commit()
    
    return ResponseModel(success=True, message="Cart item updated")


@router.delete("/remove/{cart_item_id}", response_model=ResponseModel)
def remove_from_cart(
    cart_item_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    
    return ResponseModel(success=True, message="Item removed from cart")


@router.delete("/clear", response_model=ResponseModel)
def clear_cart(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Clear all items from cart"""
    db.query(Cart).filter(Cart.user_id == current_user.id).delete()
    db.commit()
    
    return ResponseModel(success=True, message="Cart cleared")

