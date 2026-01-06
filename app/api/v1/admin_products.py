"""
Admin Product Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import Optional, List, Union
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
from app.models.product_variant import ProductVariant
from app.models.admin import Admin
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.slug import generate_slug, make_unique_slug
from app.utils.pagination import paginate
from app.api.v1.admin_upload import save_uploaded_file
from app.config import settings
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[UUID] = None,
    company: Optional[UUID] = None,
    brand: Optional[UUID] = None,
    status: Optional[str] = Query(None, pattern="^(available|unavailable|all)$"),
    stock_status: Optional[str] = Query(None, pattern="^(in_stock|low_stock|out_of_stock)$"),
    sort: Optional[str] = Query("created_at", pattern="^(name|price|stock|created_at)$"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
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
    
    # ID filters - convert UUIDs to strings for String(36) columns
    if category:
        query = query.filter(Product.category_id == str(category))
    if company:
        query = query.filter(Product.company_id == str(company))
    if brand:
        query = query.filter(Product.brand_id == str(brand))
    
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
            "variants": [
                {
                    "id": v.id,
                    "hsnCode": getattr(v, "hsn_code", None),
                    "setPieces": getattr(v, "set_pcs", None),
                    "weight": getattr(v, "weight", None),
                    "mrp": v.mrp,
                    "specialPrice": getattr(v, "special_price", None),
                    "freeItem": getattr(v, "free_item", None),
                }
                for v in getattr(p, "variants", []) or []
            ],
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
    # Convert UUID to string for database query (Product.id is String(36))
    product_id_str = str(product_id).strip()
    product_id_no_dashes = product_id_str.replace('-', '')

    product = db.query(Product)\
        .options(
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.category),
            joinedload(Product.product_images)
        )\
        .filter(Product.id.in_([product_id_str, product_id_no_dashes]))\
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
    request: Request,
    # Form fields
    name: str = Form(...),
    description: Optional[str] = Form(None),
    categoryId: Optional[str] = Form(None),  # Frontend sends as categoryId
    brand_id: Optional[str] = Form(None),
    company_id: Optional[str] = Form(None),
    mrp: Decimal = Form(...),
    sellingPrice: Decimal = Form(...),  # Frontend sends as sellingPrice
    stockQuantity: int = Form(0),  # Frontend sends as stockQuantity
    minOrderQuantity: int = Form(1),  # Frontend sends as minOrderQuantity
    unit: str = Form(...),
    piecesPerSet: int = Form(1),  # Frontend sends as piecesPerSet
    specifications: Optional[str] = Form(None),  # JSON string
    isFeatured: Optional[str] = Form("false"),  # Frontend sends as isFeatured (string)
    isAvailable: Optional[str] = Form("true"),  # Frontend sends as isAvailable (string)
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    variants: Optional[str] = Form(None),  # JSON string array of variants
    # Image files (can be single file or list)
    images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    primaryIndex: Optional[int] = Form(None),  # Index of primary image
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new product with form data and optional images"""
    # Normalize images to a list
    if images is None:
        image_files: List[UploadFile] = []
    elif isinstance(images, list):
        image_files = images
    else:
        # Single file (UploadFile or similar) -> wrap in list
        image_files = [images]

    # Validate selling price <= mrp
    if sellingPrice > mrp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be greater than MRP"
        )
    
    # Parse boolean fields (form data sends as strings)
    is_featured = isFeatured.lower() in ('true', '1', 'yes') if isFeatured else False
    is_available = isAvailable.lower() in ('true', '1', 'yes') if isAvailable else True
    
    # Parse JSON fields
    specs_dict = None
    if specifications:
        try:
            specs_dict = json.loads(specifications) if isinstance(specifications, str) else specifications
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in specifications field"
            )

    # Parse variants JSON (array of variant objects)
    variants_list: List[dict] = []
    if variants:
        try:
            raw_variants = json.loads(variants) if isinstance(variants, str) else variants
            if isinstance(raw_variants, list):
                variants_list = raw_variants
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in variants field"
            )

    # Parse/validate ID fields - keep as strings because DB uses String(36)
    category_id_str: Optional[str] = None
    if categoryId:
        try:
            # Validate UUID format but store as string
            UUID(categoryId)
            category_id_str = categoryId
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format"
            )
    
    brand_id_str: Optional[str] = None
    if brand_id:
        try:
            UUID(brand_id)
            brand_id_str = brand_id
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid brand ID format"
            )
    
    company_id_str: Optional[str] = None
    if company_id:
        try:
            UUID(company_id)
            company_id_str = company_id
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company ID format"
            )
    
    # Generate slug if not provided
    product_slug = slug or generate_slug(name)
    
    # Ensure slug is unique
    existing_slugs = [p.slug for p in db.query(Product.slug).all()]
    product_slug = make_unique_slug(product_slug, existing_slugs)
    
    # Create product
    product = Product(
        name=name,
        slug=product_slug,
        description=description,
        brand_id=brand_id_str,
        company_id=company_id_str,
        category_id=category_id_str,
        mrp=mrp,
        selling_price=sellingPrice,
        stock_quantity=stockQuantity,
        min_order_quantity=minOrderQuantity,
        unit=unit,
        pieces_per_set=piecesPerSet,
        specifications=specs_dict,
        is_featured=is_featured,
        is_available=is_available,
        meta_title=meta_title,
        meta_description=meta_description,
        # created_by column is String(36); ensure we store a string
        created_by=str(admin.id) if admin.id is not None else None
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)

    # Create variants if provided
    created_variants: List[ProductVariant] = []
    if variants_list:
        for v in variants_list:
            try:
                variant = ProductVariant(
                    product_id=product.id,
                    hsn_code=v.get("hsnCode") or v.get("hsn_code"),
                    set_pcs=v.get("setPieces") or v.get("set_pcs"),
                    weight=v.get("weight"),
                    mrp=v.get("mrp"),
                    special_price=v.get("specialPrice") or v.get("special_price"),
                    free_item=v.get("freeItem") or v.get("free_item"),
                )
                db.add(variant)
                created_variants.append(variant)
            except Exception as e:
                logger.error(f"Error creating product variant for product {product.id}: {str(e)}")

        # Optionally sync main product price from first variant
        if created_variants:
            first = created_variants[0]
            try:
                if first.mrp is not None:
                    product.mrp = first.mrp
                if first.special_price is not None:
                    product.selling_price = first.special_price
            except Exception as e:
                logger.error(f"Error syncing product price from variants for product {product.id}: {str(e)}")

        db.commit()
        db.refresh(product)
    
    # Handle image uploads if provided
    if image_files:
        uploaded_images = []
        max_display_order = db.query(func.max(ProductImage.display_order)).filter(
            ProductImage.product_id == product.id
        ).scalar() or 0
        
        for idx, image in enumerate(image_files):
            if image.filename:  # Only process if file has a name
                try:
                    # Save uploaded file (it will read the file internally)
                    image_url = save_uploaded_file(image, "product", product.id, request)
                    
                    product_image = ProductImage(
                        product_id=product.id,
                        image_url=image_url,
                        display_order=max_display_order + idx + 1,
                        is_primary=(primaryIndex is not None and idx == primaryIndex)
                    )
                    
                    db.add(product_image)
                    uploaded_images.append(product_image)
                except Exception as e:
                    # Log error but don't fail the entire request
                    logger.error(f"Error uploading image {image.filename}: {str(e)}")
        
        # If primary is set, unset other primary images
        if primaryIndex is not None and uploaded_images:
            db.query(ProductImage).filter(
                ProductImage.product_id == product.id,
                ProductImage.id.notin_([img.id for img in uploaded_images])
            ).update({"is_primary": False})
        
        db.commit()
    
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
    request: Request,
    # Form fields (all optional for partial updates)
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    categoryId: Optional[str] = Form(None),
    brand_id: Optional[str] = Form(None),
    company_id: Optional[str] = Form(None),
    mrp: Optional[Decimal] = Form(None),
    sellingPrice: Optional[Decimal] = Form(None),
    stockQuantity: Optional[int] = Form(None),
    minOrderQuantity: Optional[int] = Form(None),
    unit: Optional[str] = Form(None),
    piecesPerSet: Optional[int] = Form(None),
    specifications: Optional[str] = Form(None),
    isFeatured: Optional[str] = Form(None),
    isAvailable: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    variants: Optional[str] = Form(None),
    # Image files (optional, can be single file or list)
    images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    primaryIndex: Optional[int] = Form(None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update a product via multipart/form-data (supports images and variants)"""
    # Normalize images to a list
    if images is None:
        image_files: List[UploadFile] = []
    elif isinstance(images, list):
        image_files = images
    else:
        image_files = [images]

    # Convert UUID to string for database query (Product.id is String(36))
    product_id_str = str(product_id).strip()
    product_id_no_dashes = product_id_str.replace("-", "")

    product = (
        db.query(Product)
        .options(
            joinedload(Product.product_images),
            joinedload(Product.variants),
        )
        .filter(Product.id.in_([product_id_str, product_id_no_dashes]))
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data: dict = {}

    # Parse booleans
    if isFeatured is not None:
        is_featured = isFeatured.lower() in ("true", "1", "yes")
        product.is_featured = is_featured
        update_data["is_featured"] = is_featured
    if isAvailable is not None:
        is_available = isAvailable.lower() in ("true", "1", "yes")
        product.is_available = is_available
        update_data["is_available"] = is_available

    # Parse JSON specifications
    if specifications is not None:
        if specifications == "":
            specs_dict = None
        else:
            try:
                specs_dict = json.loads(specifications)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in specifications field",
                )
        product.specifications = specs_dict
        update_data["specifications"] = specs_dict

    # Validate/assign IDs (kept as strings)
    if categoryId is not None:
        if categoryId == "":
            product.category_id = None
            update_data["category_id"] = None
        else:
            try:
                UUID(categoryId)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format",
                )
            product.category_id = categoryId
            update_data["category_id"] = categoryId

    if brand_id is not None:
        if brand_id == "":
            product.brand_id = None
            update_data["brand_id"] = None
        else:
            try:
                UUID(brand_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid brand ID format",
                )
            product.brand_id = brand_id
            update_data["brand_id"] = brand_id

    if company_id is not None:
        if company_id == "":
            product.company_id = None
            update_data["company_id"] = None
        else:
            try:
                UUID(company_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid company ID format",
                )
            product.company_id = company_id
            update_data["company_id"] = company_id

    # Simple scalar fields
    if name is not None:
        product.name = name
        update_data["name"] = name
    if description is not None:
        product.description = description
        update_data["description"] = description
    if unit is not None:
        product.unit = unit
        update_data["unit"] = unit
    if piecesPerSet is not None:
        product.pieces_per_set = piecesPerSet
        update_data["pieces_per_set"] = piecesPerSet
    if stockQuantity is not None:
        product.stock_quantity = stockQuantity
        update_data["stock_quantity"] = stockQuantity
    if minOrderQuantity is not None:
        product.min_order_quantity = minOrderQuantity
        update_data["min_order_quantity"] = minOrderQuantity
    if meta_title is not None:
        product.meta_title = meta_title
        update_data["meta_title"] = meta_title
    if meta_description is not None:
        product.meta_description = meta_description
        update_data["meta_description"] = meta_description

    # Prices with validation
    new_mrp = mrp if mrp is not None else product.mrp
    new_selling = sellingPrice if sellingPrice is not None else product.selling_price
    if new_mrp is not None and new_selling is not None and new_selling > new_mrp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be greater than MRP",
        )

    if mrp is not None:
        product.mrp = mrp
        update_data["mrp"] = mrp
    if sellingPrice is not None:
        product.selling_price = sellingPrice
        update_data["selling_price"] = sellingPrice

    # Slug handling
    if slug is not None and slug != "":
        existing_slugs = [
            p.slug
            for p in db.query(Product.slug)
            .filter(~(Product.id.in_([product_id_str, product_id_no_dashes])))
            .all()
        ]
        new_slug = make_unique_slug(slug, existing_slugs)
        product.slug = new_slug
        update_data["slug"] = new_slug

    # Handle variants (replace existing with new list, if provided)
    if variants is not None:
        variants_list: List[dict] = []
        if variants.strip():
            try:
                raw_variants = json.loads(variants)
                if isinstance(raw_variants, list):
                    variants_list = raw_variants
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in variants field",
                )

        # Delete existing variants
        db.query(ProductVariant).filter(ProductVariant.product_id == product.id).delete()

        created_variants: List[ProductVariant] = []
        for v in variants_list:
            try:
                variant = ProductVariant(
                    product_id=product.id,
                    hsn_code=v.get("hsnCode") or v.get("hsn_code"),
                    set_pcs=v.get("setPieces") or v.get("set_pcs"),
                    weight=v.get("weight"),
                    mrp=v.get("mrp"),
                    special_price=v.get("specialPrice") or v.get("special_price"),
                    free_item=v.get("freeItem") or v.get("free_item"),
                )
                db.add(variant)
                created_variants.append(variant)
            except Exception as e:
                logger.error(
                    f"Error updating product variant for product {product.id}: {str(e)}"
                )

        # Optionally sync main product price from first variant
        if created_variants:
            first = created_variants[0]
            try:
                if first.mrp is not None:
                    product.mrp = first.mrp
                    update_data["mrp"] = first.mrp
                if first.special_price is not None:
                    product.selling_price = first.special_price
                    update_data["selling_price"] = first.special_price
            except Exception as e:
                logger.error(
                    f"Error syncing product price from variants for product {product.id}: {str(e)}"
                )

    db.commit()
    db.refresh(product)

    # Handle image uploads if provided
    if image_files:
        uploaded_images = []
        max_display_order = (
            db.query(func.max(ProductImage.display_order))
            .filter(ProductImage.product_id == product.id)
            .scalar()
            or 0
        )

        for idx, image in enumerate(image_files):
            if image.filename:
                try:
                    image_url = save_uploaded_file(image, "product", product.id, request)
                    product_image = ProductImage(
                        product_id=product.id,
                        image_url=image_url,
                        display_order=max_display_order + idx + 1,
                        is_primary=(primaryIndex is not None and idx == primaryIndex),
                    )
                    db.add(product_image)
                    uploaded_images.append(product_image)
                except Exception as e:
                    logger.error(
                        f"Error uploading image {image.filename} during product update: {str(e)}"
                    )

        if primaryIndex is not None and uploaded_images:
            db.query(ProductImage).filter(
                ProductImage.product_id == product.id,
                ProductImage.id.notin_([img.id for img in uploaded_images]),
            ).update({"is_primary": False})

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
        request=request,
    )

    return ResponseModel(
        success=True,
        data=AdminProductResponse.model_validate(product),
        message="Product updated successfully",
    )


@router.delete("/{product_id}", response_model=ResponseModel)
async def delete_product(
    product_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete a product"""
    # Convert UUID to string for database query (Product.id is String(36))
    product_id_str = str(product_id).strip()
    product_id_no_dashes = product_id_str.replace('-', '')

    product = db.query(Product).filter(Product.id.in_([product_id_str, product_id_no_dashes])).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_name = product.name
    db.delete(product)
    db.commit()
    
    # Log activity
    try:
        # entity_id in admin activity log expects a UUID; convert if possible
        entity_id_uuid = UUID(product_id_str)
    except ValueError:
        entity_id_uuid = None

    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="product_deleted",
        entity_type="product",
        entity_id=entity_id_uuid,
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
    # Convert UUID product_ids to strings for String(36) Product.id
    product_id_strs = [str(pid).strip() for pid in bulk_data.product_ids]
    product_id_strs_no_dashes = [pid.replace('-', '') for pid in product_id_strs]
    all_ids = list(set(product_id_strs + product_id_strs_no_dashes))

    products = db.query(Product).filter(Product.id.in_(all_ids)).all()
    
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

