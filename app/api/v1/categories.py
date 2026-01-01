from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.category import CategoryResponse
from app.schemas.product import ProductListResponse
from app.schemas.common import ResponseModel
from app.models.category import Category
from app.models.product import Product
from app.utils.pagination import paginate
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_categories(db: Session = Depends(get_db)):
    """Get all categories in tree structure (Mobile App API)"""
    from sqlalchemy import func
    
    all_categories = db.query(Category).filter(Category.is_active == True).all()
    
    def build_tree(parent_id=None):
        result = []
        for cat in all_categories:
            if cat.parent_id == parent_id:
                # Get product count
                product_count = db.query(func.count(Product.id)).filter(
                    Product.category_id == cat.id,
                    Product.is_available == True
                ).scalar() or 0
                
                category_data = {
                    "id": cat.id,
                    "name": cat.name,
                    "slug": cat.slug,
                    "icon": cat.icon,
                    "color": cat.color,
                    "imageUrl": None,  # Can be added later
                    "productCount": product_count,
                    "children": build_tree(cat.id)
                }
                result.append(category_data)
        
        # Sort by display_order
        result.sort(key=lambda x: x.get("displayOrder", 0))
        return result
    
    tree = build_tree()
    
    return ResponseModel(
        success=True,
        data=tree
    )


@router.get("/shop", response_model=ResponseModel)
def get_shop_categories(db: Session = Depends(get_db)):
    """Get shop categories with icon and color"""
    categories = db.query(Category).filter(Category.parent_id == None).all()
    return ResponseModel(
        success=True,
        data=[CategoryResponse.model_validate(c) for c in categories]
    )


@router.get("/{category_id}/products", response_model=ResponseModel)
def get_category_products(
    category_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get products by category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get products from this category and subcategories
    category_ids = [category_id]
    subcategories = db.query(Category).filter(Category.parent_id == category_id).all()
    category_ids.extend([c.id for c in subcategories])
    
    query = db.query(Product).filter(Product.category_id.in_(category_ids))
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    return ResponseModel(
        success=True,
        data={
            "items": [ProductListResponse.model_validate(p) for p in products],
            "pagination": paginate(products, page, limit, total)
        }
    )

