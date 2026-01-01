"""
Admin Product Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from app.database import get_db
from app.schemas.admin_product import (
    AdminProductCreate, AdminProductUpdate, AdminBulkProductUpdate,
    AdminProductResponse, AdminProductListResponse, ProductImageResponse
)
from app.schemas.common import ResponseModel
from app.models.product import Product
from app.models.brand import Brand
from app.models.company import Company
from app.models.category import Category
from app.models.product_image import ProductImage
from app.models.admin import Admin
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.slug import generate_slug, make_unique_slug
from app.utils.pagination import paginate
import os
from datetime import datetime

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[UUID] = None,
    company: Optional[UUID] = None,
    brand: Optional[UUID] = None,
    status: Optional[str] = Query(None, regex="^(available|unavailable|all)$"),
    stock_status: Optional[str] = Query(None, regex="^(in_stock|low_stock|out_of_stock)$"),
    sort: Optional[str] = Query("created_at", regex="^(name|price|stock|created_at)$"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all products with filters and pagination"""
    query = db.query(Product)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.slug.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(Product.category_id == category)
    if company:
        query = query.filter(Product.company_id == company)
    if brand:
        query = query.filter(Product.brand_id == brand)
    
    if status == "available":
        query = query.filter(Product.is_available == True)
    elif status == "unavailable":
        query = query.filter(Product.is_available == False)
    
    if stock_status == "in_stock":
        query = query.filter(Product.stock_quantity > 10)
    elif stock_status == "low_stock":
        query = query.filter(and_(Product.stock_quantity > 0, Product.stock_quantity <= 10))
    elif stock_status == "out_of_stock":
        query = query.filter(Product.stock_quantity == 0)
    
    # Apply sorting
    if sort == "name":
        order_by = Product.name.asc() if order == "asc" else Product.name.desc()
    elif sort == "price":
        order_by = Product.selling_price.asc() if order == "asc" else Product.selling_price.desc()
    elif sort == "stock":
        order_by = Product.stock_quantity.asc() if order == "asc" else Product.stock_quantity.desc()
    else:
        order_by = Product.created_at.desc() if order == "desc" else Product.created_at.asc()
    
    query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Format response
    product_list = []
    for p in products:
        product_data = {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "mrp": p.mrp,
            "sellingPrice": p.selling_price,
            "stockQuantity": p.stock_quantity,
            "minOrderQuantity": p.min_order_quantity,
            "unit": p.unit,
            "piecesPerSet": p.pieces_per_set,
            "specifications": p.specifications,
            "isFeatured": p.is_featured,
            "isAvailable": p.is_available,
            "images": [ProductImageResponse.model_validate(img) for img in p.product_images],
            "createdAt": p.created_at,
            "updatedAt": p.updated_at
        }
        
        # Add relationships
        if p.brand_rel:
            product_data["brand"] = {"id": p.brand_rel.id, "name": p.brand_rel.name}
        if p.company:
            product_data["company"] = {"id": p.company.id, "name": p.company.name}
        if p.category:
            product_data["category"] = {"id": p.category.id, "name": p.category.name, "slug": p.category.slug}
        
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
        },
        message="Products retrieved successfully"
    )


@router.get("/{product_id}", response_model=ResponseModel)
async def get_product(
    product_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get product details"""
    product = db.query(Product)\
        .options(
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.category),
            joinedload(Product.product_images)
        )\
        .filter(Product.id == product_id)\
        .first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = AdminProductResponse.model_validate(product)
    return ResponseModel(
        success=True,
        data=product_data,
        message="Product retrieved successfully"
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: AdminProductCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new product"""
    # Validate selling price <= mrp
    if product_data.selling_price > product_data.mrp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be greater than MRP"
        )
    
    # Generate slug if not provided
    slug = product_data.slug or generate_slug(product_data.name)
    
    # Ensure slug is unique
    existing_slugs = [p.slug for p in db.query(Product.slug).all()]
    slug = make_unique_slug(slug, existing_slugs)
    
    # Create product
    product = Product(
        name=product_data.name,
        slug=slug,
        description=product_data.description,
        brand_id=product_data.brand_id,
        company_id=product_data.company_id,
        category_id=product_data.category_id,
        mrp=product_data.mrp,
        selling_price=product_data.selling_price,
        stock_quantity=product_data.stock_quantity,
        min_order_quantity=product_data.min_order_quantity,
        unit=product_data.unit,
        pieces_per_set=product_data.pieces_per_set,
        specifications=product_data.specifications,
        is_featured=product_data.is_featured,
        is_available=product_data.is_available,
        meta_title=product_data.meta_title,
        meta_description=product_data.meta_description,
        created_by=admin.id
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Reload with relationships
    product = db.query(Product)\
        .options(
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.category),
            joinedload(Product.product_images)
        )\
        .filter(Product.id == product.id)\
        .first()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="product_created",
        entity_type="product",
        entity_id=product.id,
        details={"name": product.name, "slug": product.slug},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminProductResponse.model_validate(product),
        message="Product created successfully"
    )


@router.put("/{product_id}", response_model=ResponseModel)
async def update_product(
    product_id: UUID,
    product_data: AdminProductUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    
    # Handle slug update
    if "slug" in update_data and update_data["slug"]:
        existing_slugs = [p.slug for p in db.query(Product.slug).filter(Product.id != product_id).all()]
        update_data["slug"] = make_unique_slug(update_data["slug"], existing_slugs)
    
    # Validate price if both are being updated
    if "mrp" in update_data and "selling_price" in update_data:
        if update_data["selling_price"] > update_data["mrp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selling price cannot be greater than MRP"
            )
    elif "selling_price" in update_data:
        if update_data["selling_price"] > product.mrp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selling price cannot be greater than MRP"
            )
    elif "mrp" in update_data:
        if product.selling_price > update_data["mrp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MRP cannot be less than current selling price"
            )
    
    # Convert camelCase to snake_case for model fields
    field_mapping = {
        "sellingPrice": "selling_price",
        "stockQuantity": "stock_quantity",
        "minOrderQuantity": "min_order_quantity",
        "piecesPerSet": "pieces_per_set",
        "isFeatured": "is_featured",
        "isAvailable": "is_available",
        "metaTitle": "meta_title",
        "metaDescription": "meta_description"
    }
    
    for key, value in update_data.items():
        model_key = field_mapping.get(key, key)
        if hasattr(product, model_key):
            setattr(product, model_key, value)
    
    db.commit()
    db.refresh(product)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="product_updated",
        entity_type="product",
        entity_id=product.id,
        details=update_data,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminProductResponse.model_validate(product),
        message="Product updated successfully"
    )


@router.delete("/{product_id}", response_model=ResponseModel)
async def delete_product(
    product_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_name = product.name
    db.delete(product)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="product_deleted",
        entity_type="product",
        entity_id=product_id,
        details={"name": product_name},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Product deleted successfully"
    )


@router.post("/bulk-update", response_model=ResponseModel)
async def bulk_update_products(
    bulk_data: AdminBulkProductUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Bulk update products"""
    products = db.query(Product).filter(Product.id.in_(bulk_data.product_ids)).all()
    
    if len(products) != len(bulk_data.product_ids):
        raise HTTPException(
            status_code=404,
            detail="Some products not found"
        )
    
    # Field mapping
    field_mapping = {
        "stockQuantity": "stock_quantity",
        "isAvailable": "is_available",
        "isFeatured": "is_featured"
    }
    
    updated_count = 0
    for product in products:
        for key, value in bulk_data.updates.items():
            model_key = field_mapping.get(key, key)
            if hasattr(product, model_key):
                setattr(product, model_key, value)
        updated_count += 1
    
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="products_bulk_updated",
        entity_type="product",
        details={
            "product_ids": [str(pid) for pid in bulk_data.product_ids],
            "updates": bulk_data.updates,
            "count": updated_count
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={"updated_count": updated_count},
        message=f"{updated_count} products updated successfully"
    )


@router.post("/{product_id}/images", response_model=ResponseModel)
async def upload_product_images(
    product_id: UUID,
    request: Request,
    images: List[UploadFile] = File(...),
    primary_index: Optional[int] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Upload product images"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # TODO: Implement actual file upload to cloud storage (S3, Cloudinary, etc.)
    # For now, we'll just create placeholder records
    # In production, upload files and get URLs
    
    uploaded_images = []
    max_display_order = db.query(func.max(ProductImage.display_order)).filter(
        ProductImage.product_id == product_id
    ).scalar() or 0
    
    for idx, image in enumerate(images):
        # In production: upload to cloud storage and get URL
        # For now, use a placeholder
        image_url = f"https://cdn.dely.com/products/{product_id}/{image.filename}"
        
        product_image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            display_order=max_display_order + idx + 1,
            is_primary=(primary_index is not None and idx == primary_index)
        )
        
        db.add(product_image)
        uploaded_images.append(product_image)
    
    # If primary is set, unset other primary images
    if primary_index is not None:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.id.notin_([img.id for img in uploaded_images])
        ).update({"is_primary": False})
    
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="product_images_uploaded",
        entity_type="product",
        entity_id=product_id,
        details={"image_count": len(images)},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "images": [ProductImageResponse.model_validate(img) for img in uploaded_images]
        },
        message="Images uploaded successfully"
    )

