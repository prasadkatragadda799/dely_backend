from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.wishlist import WishlistAdd, WishlistResponse
from app.schemas.common import ResponseModel
from app.models.wishlist import Wishlist
from app.models.product import Product
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_wishlist(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's wishlist"""
    wishlist_items = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id
    ).all()
    
    items = []
    for item in wishlist_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            from app.schemas.product import ProductListResponse
            items.append(WishlistResponse(
                id=item.id,
                product_id=item.product_id,
                product=ProductListResponse.model_validate(product),
                created_at=item.created_at
            ))
    
    return ResponseModel(success=True, data=items)


@router.post("/add", response_model=ResponseModel)
def add_to_wishlist(
    wishlist_data: WishlistAdd,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add product to wishlist"""
    product = db.query(Product).filter(Product.id == wishlist_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already in wishlist
    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == wishlist_data.product_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Product already in wishlist")
    
    wishlist_item = Wishlist(
        user_id=current_user.id,
        product_id=wishlist_data.product_id
    )
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    
    return ResponseModel(
        success=True,
        message="Product added to wishlist"
    )


@router.delete("/remove/{product_id}", response_model=ResponseModel)
def remove_from_wishlist(
    product_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove product from wishlist"""
    wishlist_item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == product_id
    ).first()
    
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Product not in wishlist")
    
    db.delete(wishlist_item)
    db.commit()
    
    return ResponseModel(success=True, message="Product removed from wishlist")

