"""
Seller Product Management Endpoints
Sellers can only manage products for their assigned company
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from decimal import Decimal
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.admin_product import AdminProductCreate, AdminProductUpdate
from app.models.admin import Admin, AdminRole
from app.models.product import Product
from app.models.category import Category
from app.models.brand import Brand
from app.models.company import Company
from app.api.admin_deps import require_seller_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.slug import generate_slug

router = APIRouter()


def check_seller_product_access(seller: Admin, product: Product) -> bool:
    """
    Check if seller has access to this product.
    Sellers can only access products from their company.
    Admins and above can access all products.
    """
    if seller.role in [AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MANAGER]:
        return True
    
    if seller.role == AdminRole.SELLER:
        return product.company_id == seller.company_id
    
    return False


@router.get("", response_model=ResponseModel)
async def list_seller_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    is_available: Optional[bool] = None,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    List products for the current seller.
    Sellers only see products from their company.
    Admins see all products.
    """
    query = db.query(Product)
    
    # Sellers can only see products from their company
    if seller.role == AdminRole.SELLER:
        if not seller.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller not assigned to any company"
            )
        query = query.filter(Product.company_id == seller.company_id)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.slug.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if is_available is not None:
        query = query.filter(Product.is_available == is_available)
    
    # Order by created_at descending
    query = query.order_by(Product.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Format response
    product_list = []
    for p in products:
        product_data = {
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "mrp": float(p.mrp) if p.mrp else 0.0,
            "selling_price": float(p.selling_price) if p.selling_price else 0.0,
            "stock_quantity": p.stock_quantity,
            "is_available": p.is_available,
            "is_featured": p.is_featured,
            "category": {
                "id": p.category.id,
                "name": p.category.name
            } if p.category else None,
            "company": {
                "id": p.company.id,
                "name": p.company.name
            } if p.company else None,
            "images": [{
                "url": img.image_url,
                "is_primary": img.is_primary
            } for img in p.product_images] if p.product_images else [],
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        product_list.append(product_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": product_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 0
            }
        },
        message="Products retrieved successfully"
    )


@router.get("/{product_id}", response_model=ResponseModel)
async def get_seller_product(
    product_id: str,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Get product details.
    Sellers can only view products from their company.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check access
    if not check_seller_product_access(seller, product):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view products from your company."
        )
    
    # Format response
    product_data = {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "mrp": float(product.mrp) if product.mrp else 0.0,
        "selling_price": float(product.selling_price) if product.selling_price else 0.0,
        "stock_quantity": product.stock_quantity,
        "min_order_quantity": product.min_order_quantity,
        "unit": product.unit,
        "pieces_per_set": product.pieces_per_set,
        "specifications": product.specifications,
        "is_featured": product.is_featured,
        "is_available": product.is_available,
        "meta_title": product.meta_title,
        "meta_description": product.meta_description,
        "category": {
            "id": product.category.id,
            "name": product.category.name
        } if product.category else None,
        "brand": {
            "id": product.brand_rel.id,
            "name": product.brand_rel.name
        } if product.brand_rel else None,
        "company": {
            "id": product.company.id,
            "name": product.company.name
        } if product.company else None,
        "images": [{
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.is_primary,
            "display_order": img.display_order
        } for img in product.product_images] if product.product_images else [],
        "variants": [{
            "id": v.id,
            "hsn_code": v.hsn_code,
            "set_pcs": v.set_pcs,
            "weight": v.weight,
            "mrp": float(v.mrp) if v.mrp else 0.0,
            "special_price": float(v.special_price) if v.special_price else 0.0,
            "free_item": v.free_item
        } for v in product.variants] if product.variants else [],
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=product_data,
        message="Product retrieved successfully"
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_seller_product(
    product_data: AdminProductCreate,
    request: Request,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Create a new product.
    Sellers can only create products for their assigned company.
    """
    # Sellers must create products for their company only
    if seller.role == AdminRole.SELLER:
        if not seller.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller not assigned to any company"
            )
        # Override company_id with seller's company
        product_data.company_id = seller.company_id
    
    # Verify category exists
    category = db.query(Category).filter(Category.id == str(product_data.category_id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Generate slug
    slug = generate_slug(product_data.name)
    
    # Check if slug exists
    existing_product = db.query(Product).filter(Product.slug == slug).first()
    if existing_product:
        # Add random suffix
        import random
        slug = f"{slug}-{random.randint(1000, 9999)}"
    
    # Create product
    new_product = Product(
        name=product_data.name,
        slug=slug,
        description=product_data.description,
        brand_id=str(product_data.brand_id) if product_data.brand_id else None,
        company_id=str(product_data.company_id),
        category_id=str(product_data.category_id),
        mrp=product_data.mrp,
        selling_price=product_data.selling_price,
        stock_quantity=product_data.stock_quantity or 0,
        min_order_quantity=product_data.min_order_quantity or 1,
        unit=product_data.unit,
        pieces_per_set=product_data.pieces_per_set or 1,
        specifications=product_data.specifications,
        is_featured=product_data.is_featured or False,
        is_available=product_data.is_available if product_data.is_available is not None else True,
        meta_title=product_data.meta_title,
        meta_description=product_data.meta_description,
        created_by=str(seller.id)
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_created",
        entity_type="product",
        entity_id=UUID(str(new_product.id)),
        details={
            "product_name": new_product.name,
            "company_id": new_product.company_id
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": str(new_product.id),
            "name": new_product.name,
            "slug": new_product.slug
        },
        message="Product created successfully"
    )


@router.put("/{product_id}", response_model=ResponseModel)
async def update_seller_product(
    product_id: str,
    product_data: AdminProductUpdate,
    request: Request,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Update a product.
    Sellers can only update products from their company.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check access
    if not check_seller_product_access(seller, product):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update products from your company."
        )
    
    # Update fields
    if product_data.name is not None:
        product.name = product_data.name
        product.slug = generate_slug(product_data.name)
    
    if product_data.description is not None:
        product.description = product_data.description
    
    if product_data.mrp is not None:
        product.mrp = product_data.mrp
    
    if product_data.selling_price is not None:
        product.selling_price = product_data.selling_price
    
    if product_data.stock_quantity is not None:
        product.stock_quantity = product_data.stock_quantity
    
    if product_data.is_available is not None:
        product.is_available = product_data.is_available
    
    if product_data.is_featured is not None:
        product.is_featured = product_data.is_featured
    
    db.commit()
    db.refresh(product)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_updated",
        entity_type="product",
        entity_id=UUID(str(product.id)),
        details={
            "product_name": product.name
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug
        },
        message="Product updated successfully"
    )


@router.delete("/{product_id}", response_model=ResponseModel)
async def delete_seller_product(
    product_id: str,
    request: Request,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Delete a product (soft delete - sets is_available to False).
    Sellers can only delete products from their company.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check access
    if not check_seller_product_access(seller, product):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only delete products from your company."
        )
    
    # Soft delete
    product.is_available = False
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_deleted",
        entity_type="product",
        entity_id=UUID(str(product.id)),
        details={
            "product_name": product.name
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Product deleted successfully"
    )


@router.get("/statistics/overview", response_model=ResponseModel)
async def get_seller_statistics(
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Get statistics for seller's products.
    Sellers only see stats for their company products.
    """
    query = db.query(Product)
    
    # Sellers can only see products from their company
    if seller.role == AdminRole.SELLER:
        if not seller.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller not assigned to any company"
            )
        query = query.filter(Product.company_id == seller.company_id)
    
    total_products = query.count()
    active_products = query.filter(Product.is_available == True).count()
    out_of_stock = query.filter(Product.stock_quantity == 0).count()
    low_stock = query.filter(
        and_(
            Product.stock_quantity > 0,
            Product.stock_quantity <= 10
        )
    ).count()
    
    return ResponseModel(
        success=True,
        data={
            "total_products": total_products,
            "active_products": active_products,
            "inactive_products": total_products - active_products,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock
        },
        message="Statistics retrieved successfully"
    )


@router.get("/brands", response_model=ResponseModel)
async def list_seller_brands(
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    List brands for sellers.
    Sellers can see all brands (needed for product creation).
    """
    query = db.query(Brand)
    
    # If seller has a company, prioritize brands from their company
    # but still show all brands (sellers might need to see all brands for reference)
    brands = query.all()
    
    brand_list = []
    for brand in brands:
        brand_data = {
            "id": brand.id,
            "name": brand.name,
            "logoUrl": brand.logo_url,
            "createdAt": brand.created_at.isoformat() if brand.created_at else None,
            "updatedAt": brand.updated_at.isoformat() if brand.updated_at else None
        }
        
        if brand.company:
            brand_data["company"] = {
                "id": brand.company.id,
                "name": brand.company.name
            }
        
        if brand.category:
            brand_data["category"] = {
                "id": brand.category.id,
                "name": brand.category.name
            }
        
        brand_list.append(brand_data)
    
    return ResponseModel(
        success=True,
        data=brand_list,
        message="Brands retrieved successfully"
    )


@router.get("/categories", response_model=ResponseModel)
async def list_seller_categories(
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    List categories for sellers.
    Sellers can see all categories (needed for product creation).
    """
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    category_list = []
    for category in categories:
        category_data = {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "imageUrl": category.image_url,
            "iconUrl": category.icon_url,
            "displayOrder": category.display_order,
            "isActive": category.is_active,
            "createdAt": category.created_at.isoformat() if category.created_at else None,
            "updatedAt": category.updated_at.isoformat() if category.updated_at else None
        }
        category_list.append(category_data)
    
    return ResponseModel(
        success=True,
        data=category_list,
        message="Categories retrieved successfully"
    )


@router.get("/companies", response_model=ResponseModel)
async def list_seller_companies(
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    List companies for sellers.
    Sellers with assigned company see only their company.
    Managers and above see all companies.
    """
    
    if seller.role == AdminRole.SELLER:
        # Sellers see only their assigned company
        if not seller.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller not assigned to any company"
            )
        companies = db.query(Company).filter(Company.id == seller.company_id).all()
    else:
        # Managers and above see all companies
        companies = db.query(Company).all()
    
    company_list = []
    for company in companies:
        company_data = {
            "id": company.id,
            "name": company.name,
            "description": company.description,
            "logoUrl": company.logo_url or company.logo,
            "createdAt": company.created_at.isoformat() if company.created_at else None,
            "updatedAt": company.updated_at.isoformat() if company.updated_at else None
        }
        company_list.append(company_data)
    
    return ResponseModel(
        success=True,
        data=company_list,
        message="Companies retrieved successfully"
    )
