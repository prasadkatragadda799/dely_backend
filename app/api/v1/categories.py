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
                    "image_url": cat.image if hasattr(cat, 'image') and cat.image else None,
                    "product_count": product_count,
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
    category_id_str = str(category_id)
    category = db.query(Category).filter(Category.id == category_id_str).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get products from this category and subcategories
    category_ids = [category_id_str]
    subcategories = db.query(Category).filter(Category.parent_id == category_id_str).all()
    category_ids.extend([str(c.id) for c in subcategories])
    
    query = db.query(Product).filter(
        Product.category_id.in_(category_ids),
        Product.is_available == True
    )
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Format products manually to handle None values and match main products endpoint structure
    product_list = []
    for p in products:
        # Calculate discount percentage
        discount = 0.0
        if p.mrp and p.selling_price and p.mrp > 0:
            discount = float(((p.mrp - p.selling_price) / p.mrp) * 100)
        
        product_data = {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "mrp": float(p.mrp) if p.mrp else None,
            "sellingPrice": float(p.selling_price) if p.selling_price else None,
            "discount": round(discount, 2),
            "stockQuantity": p.stock_quantity,
            "minOrderQuantity": p.min_order_quantity,
            "unit": p.unit,
            "piecesPerSet": p.pieces_per_set,
            "specifications": p.specifications or {},
            "isFeatured": p.is_featured,
            "isAvailable": p.is_available,
            "images": [],
            "variants": [
                {
                    "id": v.id,
                    "hsnCode": getattr(v, "hsn_code", None),
                    "setPieces": getattr(v, "set_pcs", None),
                    "weight": getattr(v, "weight", None),
                    "mrp": float(v.mrp) if v.mrp is not None else None,
                    "specialPrice": float(getattr(v, "special_price")) if getattr(v, "special_price", None) is not None else None,
                    "freeItem": getattr(v, "free_item", None),
                }
                for v in getattr(p, "variants", []) or []
            ],
            "createdAt": p.created_at.isoformat() if p.created_at else None
        }
        
        # Add brand information
        if p.brand_rel:
            product_data["brand"] = {
                "id": p.brand_rel.id,
                "name": p.brand_rel.name,
                "logoUrl": p.brand_rel.logo_url
            }
        elif hasattr(p, 'brand') and p.brand:
            product_data["brand"] = p.brand
        
        # Add company information
        if p.company:
            product_data["company"] = {
                "id": p.company.id,
                "name": p.company.name,
                "logoUrl": p.company.logo_url or p.company.logo
            }
        
        # Add category information
        if p.category:
            product_data["category"] = {
                "id": p.category.id,
                "name": p.category.name,
                "slug": p.category.slug
            }
        
        # Add product images
        if p.product_images:
            product_data["images"] = [{
                "url": img.image_url,
                "isPrimary": img.is_primary
            } for img in sorted(p.product_images, key=lambda x: x.display_order)]
        elif p.images:  # Fallback to legacy images field
            if isinstance(p.images, list):
                product_data["images"] = [{"url": img, "isPrimary": idx == 0} for idx, img in enumerate(p.images)]
        
        # Add rating (for future reviews feature)
        product_data["rating"] = float(p.rating) if p.rating else 0.0
        product_data["reviewCount"] = p.reviews_count or 0
        
        product_list.append(product_data)
    
    return ResponseModel(
        success=True,
        data={
            "products": product_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    )

