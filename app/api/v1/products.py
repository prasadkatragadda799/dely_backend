from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import get_db
from app.schemas.product import ProductResponse, ProductListResponse
from app.schemas.common import ResponseModel, PaginatedResponse, PaginationModel
from app.models.product import Product
from app.models.company import Company
from app.models.category import Category
from app.utils.pagination import paginate
from typing import Optional
from decimal import Decimal
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    company: Optional[UUID] = None,
    brand: Optional[UUID] = None,
    search: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sort: Optional[str] = Query("created_at", pattern="^(price_asc|price_desc|name|popularity|created_at)$"),
    featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all products with filters (Mobile App API)"""
    query = db.query(Product).filter(Product.is_available == True)
    
    # Apply filters (convert UUIDs to strings for database queries)
    if category:
        query = query.filter(Product.category_id == str(category))
    if company:
        query = query.filter(Product.company_id == str(company))
    if brand:
        query = query.filter(Product.brand_id == str(brand))
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.slug.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    if min_price:
        query = query.filter(Product.selling_price >= min_price)
    if max_price:
        query = query.filter(Product.selling_price <= max_price)
    if featured is not None:
        query = query.filter(Product.is_featured == featured)
    
    # Apply sorting
    if sort == "price_asc":
        order_by = Product.selling_price.asc()
    elif sort == "price_desc":
        order_by = Product.selling_price.desc()
    elif sort == "name":
        order_by = Product.name.asc()
    elif sort == "popularity":
        # Sort by featured first, then by created_at
        order_by = Product.is_featured.desc(), Product.created_at.desc()
    else:
        order_by = Product.created_at.desc()
    
    if isinstance(order_by, tuple):
        query = query.order_by(*order_by)
    else:
        query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Format products with enhanced data
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
            "createdAt": p.created_at.isoformat() if p.created_at else None
        }
        
        # Add variants (if any)
        if hasattr(p, "variants") and p.variants:
            product_data["variants"] = [
                {
                    "id": v.id,
                    "hsnCode": getattr(v, "hsn_code", None),
                    "setPieces": getattr(v, "set_pcs", None),
                    "weight": getattr(v, "weight", None),
                    "mrp": float(v.mrp) if v.mrp is not None else None,
                    "specialPrice": float(getattr(v, "special_price")) if getattr(v, "special_price", None) is not None else None,
                    "freeItem": getattr(v, "free_item", None),
                }
                for v in p.variants
            ]
        else:
            product_data["variants"] = []

        # Add brand information
        if p.brand_rel:
            product_data["brand"] = {
                "id": p.brand_rel.id,
                "name": p.brand_rel.name,
                "logoUrl": p.brand_rel.logo_url
            }
        
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


@router.get("/{product_id}", response_model=ResponseModel)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Get product details by ID (Mobile App API)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=404, detail="Product not available")
    
    # Calculate discount
    discount = 0.0
    if product.mrp and product.selling_price and product.mrp > 0:
        discount = float(((product.mrp - product.selling_price) / product.mrp) * 100)
    
    product_data = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "mrp": float(product.mrp) if product.mrp else None,
        "sellingPrice": float(product.selling_price) if product.selling_price else None,
        "discount": round(discount, 2),
        "stockQuantity": product.stock_quantity,
        "minOrderQuantity": product.min_order_quantity,
        "unit": product.unit,
        "piecesPerSet": product.pieces_per_set,
        "specifications": product.specifications or {},
        "isFeatured": product.is_featured,
        "isAvailable": product.is_available,
        "images": [],
        "rating": float(product.rating) if product.rating else 0.0,
        "reviewCount": product.reviews_count or 0,
        "createdAt": product.created_at.isoformat() if product.created_at else None
    }
    
    # Add variants
    if hasattr(product, "variants") and product.variants:
        product_data["variants"] = [
            {
                "id": v.id,
                "hsnCode": getattr(v, "hsn_code", None),
                "setPieces": getattr(v, "set_pcs", None),
                "weight": getattr(v, "weight", None),
                "mrp": float(v.mrp) if v.mrp is not None else None,
                "specialPrice": float(getattr(v, "special_price")) if getattr(v, "special_price", None) is not None else None,
                "freeItem": getattr(v, "free_item", None),
            }
            for v in product.variants
        ]
    else:
        product_data["variants"] = []

    # Add brand
    if product.brand_rel:
        product_data["brand"] = {
            "id": product.brand_rel.id,
            "name": product.brand_rel.name,
            "logoUrl": product.brand_rel.logo_url
        }
    
    # Add company
    if product.company:
        product_data["company"] = {
            "id": product.company.id,
            "name": product.company.name,
            "logoUrl": product.company.logo_url or product.company.logo
        }
    
    # Add category
    if product.category:
        product_data["category"] = {
            "id": product.category.id,
            "name": product.category.name,
            "slug": product.category.slug
        }
    
    # Add images
    if product.product_images:
        product_data["images"] = [{
            "url": img.image_url,
            "isPrimary": img.is_primary
        } for img in sorted(product.product_images, key=lambda x: x.display_order)]
    elif product.images:
        if isinstance(product.images, list):
            product_data["images"] = [{"url": img, "isPrimary": idx == 0} for idx, img in enumerate(product.images)]
    
    # TODO: Add related products and reviews in future
    
    return ResponseModel(
        success=True,
        data=product_data
    )


@router.get("/slug/{slug}", response_model=ResponseModel)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get product details by slug (Mobile App API)"""
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=404, detail="Product not available")
    
    # Use same formatting as get_product
    discount = 0.0
    if product.mrp and product.selling_price and product.mrp > 0:
        discount = float(((product.mrp - product.selling_price) / product.mrp) * 100)
    
    product_data = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "mrp": float(product.mrp) if product.mrp else None,
        "sellingPrice": float(product.selling_price) if product.selling_price else None,
        "discount": round(discount, 2),
        "stockQuantity": product.stock_quantity,
        "minOrderQuantity": product.min_order_quantity,
        "unit": product.unit,
        "piecesPerSet": product.pieces_per_set,
        "specifications": product.specifications or {},
        "isFeatured": product.is_featured,
        "isAvailable": product.is_available,
        "images": [],
        "rating": float(product.rating) if product.rating else 0.0,
        "reviewCount": product.reviews_count or 0,
        "createdAt": product.created_at.isoformat() if product.created_at else None
    }
    
    if product.brand_rel:
        product_data["brand"] = {
            "id": product.brand_rel.id,
            "name": product.brand_rel.name,
            "logoUrl": product.brand_rel.logo_url
        }
    
    if product.company:
        product_data["company"] = {
            "id": product.company.id,
            "name": product.company.name,
            "logoUrl": product.company.logo_url or product.company.logo
        }
    
    if product.category:
        product_data["category"] = {
            "id": product.category.id,
            "name": product.category.name,
            "slug": product.category.slug
        }
    
    if product.product_images:
        product_data["images"] = [{
            "url": img.image_url,
            "isPrimary": img.is_primary
        } for img in sorted(product.product_images, key=lambda x: x.display_order)]
    elif product.images:
        if isinstance(product.images, list):
            product_data["images"] = [{"url": img, "isPrimary": idx == 0} for idx, img in enumerate(product.images)]
    
    return ResponseModel(
        success=True,
        data=product_data
    )


@router.get("/search", response_model=ResponseModel)
def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    company: Optional[UUID] = None,
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Search products"""
    query = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.brand.ilike(f"%{q}%"),
            Product.description.ilike(f"%{q}%")
        )
    )
    
    if category:
        query = query.filter(Product.category_id == category)
    if company:
        query = query.filter(Product.company_id == company)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    
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


@router.get("/featured", response_model=ResponseModel)
def get_featured_products(
    limit: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get featured products"""
    products = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_available == True
    ).limit(limit).all()
    
    # Format products with enhanced data (matching get_products structure)
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
                    "mrp": float(v.mrp) if v.mrp else None,
                    "specialPrice": float(v.special_price) if v.special_price else None,
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
            "items": product_list
        }
    )


@router.get("/company/{company_name}", response_model=ResponseModel)
def get_products_by_company(
    company_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get products by company name"""
    company = db.query(Company).filter(Company.name.ilike(f"%{company_name}%")).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(Product).filter(Product.company_id == company.id)
    if category:
        query = query.filter(Product.category_id == category)
    
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


@router.get("/brand/{brand_name}", response_model=ResponseModel)
def get_products_by_brand(
    brand_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get products by brand name"""
    query = db.query(Product).filter(Product.brand.ilike(f"%{brand_name}%"))
    if category:
        query = query.filter(Product.category_id == category)
    
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

