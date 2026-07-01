"""
Seller Product Management Endpoints
Sellers can manage products across companies (as requested).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List, Union
from uuid import UUID
from datetime import date, timedelta
from pydantic import BaseModel
from decimal import Decimal
import json
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.admin import Admin, AdminRole
from app.models.product import Product
from app.models.product_service_area import ProductServiceArea
from app.models.category import Category
from app.models.brand import Brand
from app.models.company import Company
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.api.admin_deps import require_seller_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.slug import generate_slug, make_unique_slug
from app.utils.packaging_label import normalize_packaging_label_type
from app.api.v1.admin_upload import save_uploaded_file

router = APIRouter()


def _normalize_pieces_per_set(unit: Optional[str], pieces_per_set: Optional[int]) -> int:
    u = str(unit or "piece").strip().lower()
    if u == "piece":
        return 1
    n = int(pieces_per_set) if pieces_per_set is not None else 1
    return max(1, n)


def check_seller_product_access(seller: Admin, product: Product) -> bool:
    """
    Check if seller has access to this product.
    Sellers can only access products from their company.
    Admins and above can access all products.
    """
    if seller.role in [AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MANAGER]:
        return True
    
    if seller.role == AdminRole.SELLER:
        # Sellers should only manage products created by them.
        return str(product.created_by) == str(seller.id)
    
    return False


@router.get("", response_model=ResponseModel)
async def list_seller_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    is_available: Optional[bool] = None,
    expiry_within_months: Optional[int] = Query(None, ge=1, le=24),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    List products for the current seller.
    Sellers only see products from their company.
    Admins see all products.
    """
    query = db.query(Product)
    
    # Sellers should only see products created by them.
    if seller.role == AdminRole.SELLER:
        query = query.filter(Product.created_by == str(seller.id))
    
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
    
    # Filter by products expiring within N months (inventory management)
    if expiry_within_months is not None:
        today = date.today()
        end_date = today + timedelta(days=expiry_within_months * 30)
        query = query.filter(
            Product.expiry_date.isnot(None),
            Product.expiry_date >= today,
            Product.expiry_date <= end_date,
        )
    
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
            "expiry_date": p.expiry_date.isoformat() if getattr(p, "expiry_date", None) else None,
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
            detail="Access denied. You can only view products created by you."
        )
    
    # Format response
    product_data = {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "hsnCode": getattr(product, "hsn_code", None),
        "hsn_code": getattr(product, "hsn_code", None),
        "mrp": float(product.mrp) if product.mrp else 0.0,
        "selling_price": float(product.selling_price) if product.selling_price else 0.0,
        "stock_quantity": product.stock_quantity,
        "min_order_quantity": product.min_order_quantity,
        "unit": product.unit,
        "pieces_per_set": product.pieces_per_set,
        "specifications": product.specifications,
        "is_featured": product.is_featured,
        "is_available": product.is_available,
        "expiry_date": product.expiry_date.isoformat() if getattr(product, "expiry_date", None) else None,
        "manufacturer_name": getattr(product, "manufacturer_name", None),
        "manufacturer_address": getattr(product, "manufacturer_address", None),
        "cancel_policy": getattr(product, "cancel_policy", None),
        "return_policy": getattr(product, "return_policy", None),
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
            "id": str(img.id),
            "imageUrl": img.image_url,
            "image_url": img.image_url,
            "is_primary": img.is_primary,
            "display_order": img.display_order
        } for img in product.product_images] if product.product_images else [],
        "variants": [{
            "id": str(v.id),
            "hsnCode": v.hsn_code,
            "hsn_code": v.hsn_code,
            "packagingLabelType": getattr(v, "packaging_label_type", None),
            "packaging_label_type": getattr(v, "packaging_label_type", None),
            "setPieces": v.set_pcs,
            "set_pcs": v.set_pcs,
            "weight": v.weight,
            "mrp": float(v.mrp) if v.mrp else 0.0,
            "specialPrice": float(v.special_price) if v.special_price else 0.0,
            "special_price": float(v.special_price) if v.special_price else 0.0,
            "freeItem": v.free_item,
            "free_item": v.free_item,
            "minOrderQuantity": getattr(v, "min_order_quantity", 1) or 1,
            "min_order_quantity": getattr(v, "min_order_quantity", 1) or 1,
            "cgst": float(getattr(v, "cgst", 0) or 0),
            "sgst": float(getattr(v, "sgst", 0) or 0),
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
    request: Request,
    # Multipart form fields (match admin product create)
    name: str = Form(...),
    description: Optional[str] = Form(None),
    categoryId: Optional[str] = Form(None),  # camelCase
    category_id: Optional[str] = Form(None),  # snake_case
    divisionId: Optional[str] = Form(None),  # camelCase
    division_id: Optional[str] = Form(None),  # snake_case
    brand_id: Optional[str] = Form(None),
    brandId: Optional[str] = Form(None),
    company_id: Optional[str] = Form(None),
    companyId: Optional[str] = Form(None),
    mrp: Optional[Decimal] = Form(None),
    sellingPrice: Optional[Decimal] = Form(None),
    selling_price: Optional[Decimal] = Form(None),  # allow snake_case too
    stockQuantity: Optional[int] = Form(None),
    stock_quantity: Optional[int] = Form(None),
    minOrderQuantity: Optional[int] = Form(None),
    min_order_quantity: Optional[int] = Form(None),
    unit: str = Form(...),
    piecesPerSet: Optional[int] = Form(None),
    pieces_per_set: Optional[int] = Form(None),
    hsnCode: Optional[str] = Form(None),
    hsn_code: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),  # JSON string
    isFeatured: Optional[str] = Form(None),
    is_featured: Optional[str] = Form(None),
    isAvailable: Optional[str] = Form(None),
    is_available: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    metaTitle: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    metaDescription: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    expiryDate: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    manufacturerName: Optional[str] = Form(None),
    manufacturerAddress: Optional[str] = Form(None),
    cancelPolicy: Optional[str] = Form(None),
    returnPolicy: Optional[str] = Form(None),
    variants: Optional[str] = Form(None),  # JSON string array of variants
    images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    primaryIndex: Optional[int] = Form(None),
    primary_index: Optional[int] = Form(None),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Create a new product.
    Sellers can create products across companies (as requested).
    """

    # Normalize images to list
    if images is None:
        image_files: List[UploadFile] = []
    elif isinstance(images, list):
        image_files = images
    else:
        image_files = [images]

    # Normalize field variants
    categoryId = categoryId or category_id
    division_id_param = divisionId or division_id
    brand_id = brand_id or brandId
    company_id = company_id or companyId
    sellingPrice = sellingPrice if sellingPrice is not None else (selling_price if selling_price is not None else Decimal("0"))
    if mrp is None:
        mrp = Decimal("0")
    stockQuantity = stockQuantity if stockQuantity is not None else stock_quantity
    minOrderQuantity = minOrderQuantity if minOrderQuantity is not None else min_order_quantity
    piecesPerSet = piecesPerSet if piecesPerSet is not None else pieces_per_set
    isFeatured = isFeatured if isFeatured is not None else is_featured
    isAvailable = isAvailable if isAvailable is not None else is_available
    meta_title = meta_title if meta_title is not None else metaTitle
    meta_description = meta_description if meta_description is not None else metaDescription
    primaryIndex = primaryIndex if primaryIndex is not None else primary_index
    expiry_date_str = expiryDate or expiry_date

    # Validate IDs (DB stores strings but validate UUID format)
    if not categoryId:
        raise HTTPException(status_code=400, detail="categoryId/category_id is required")
    try:
        UUID(categoryId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category ID format")
    category_id_str = categoryId

    division_id_str: Optional[str] = None
    if division_id_param:
        try:
            UUID(division_id_param)
            division_id_str = division_id_param
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid division ID format")

    brand_id_str: Optional[str] = None
    if brand_id:
        try:
            UUID(brand_id)
            brand_id_str = brand_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid brand ID format")

    if not company_id:
        raise HTTPException(status_code=400, detail="companyId/company_id is required for seller product creation")
    try:
        UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID format")
    company_id_str = company_id

    # Verify category exists
    category = db.query(Category).filter(Category.id == str(category_id_str)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Generate slug
    product_slug = slug or generate_slug(name)
    
    # Check if slug exists
    existing_product = db.query(Product).filter(Product.slug == product_slug).first()
    if existing_product:
        # Add random suffix
        import random
        product_slug = f"{product_slug}-{random.randint(1000, 9999)}"
    
    # Create product
    new_product = Product(
        name=name,
        slug=product_slug,
        description=description,
        brand_id=brand_id_str,
        company_id=company_id_str,
        category_id=category_id_str,
        division_id=division_id_str,
        mrp=mrp,
        selling_price=sellingPrice,
        stock_quantity=int(stockQuantity) if stockQuantity is not None else 0,
        min_order_quantity=int(minOrderQuantity) if minOrderQuantity is not None else 1,
        unit=unit,
        pieces_per_set=_normalize_pieces_per_set(unit, piecesPerSet),
        specifications=specifications,
        is_featured=(str(isFeatured).lower() in ("true", "1", "yes")) if isFeatured is not None else False,
        is_available=(str(isAvailable).lower() in ("true", "1", "yes")) if isAvailable is not None else True,
        expiry_date=date.fromisoformat(expiry_date_str.strip()) if expiry_date_str else None,
        hsn_code=hsnCode or hsn_code or None,
        meta_title=meta_title,
        meta_description=meta_description,
        manufacturer_name=manufacturerName or None,
        manufacturer_address=manufacturerAddress or None,
        cancel_policy=cancelPolicy or None,
        return_policy=returnPolicy or None,
        created_by=str(seller.id)
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Handle image uploads if provided
    if image_files:
        uploaded_images: List[ProductImage] = []
        for idx, image in enumerate(image_files):
            try:
                image_url = save_uploaded_file(image, "product", new_product.id, request)
                product_image = ProductImage(
                    product_id=new_product.id,
                    image_url=image_url,
                    display_order=idx,
                    is_primary=(primaryIndex is not None and idx == int(primaryIndex)),
                )
                db.add(product_image)
                uploaded_images.append(product_image)
            except Exception:
                # Don't fail entire create if an image fails; keep product created.
                continue
        db.commit()

    # Save variants if provided
    if variants:
        try:
            variants_list = json.loads(variants) if isinstance(variants, str) else variants
        except (ValueError, TypeError):
            variants_list = []
        if isinstance(variants_list, list):
            for v in variants_list:
                ptype = normalize_packaging_label_type(v.get("packagingLabelType") or "")
                new_variant = ProductVariant(
                    product_id=str(new_product.id),
                    hsn_code=v.get("hsnCode") or "",
                    packaging_label_type=ptype,
                    set_pcs=v.get("setPieces") or "",
                    weight=v.get("weight") or "",
                    mrp=Decimal(str(v.get("mrp") or 0)),
                    special_price=Decimal(str(v.get("specialPrice") or 0)),
                    free_item=v.get("freeItem") or "",
                    min_order_quantity=int(v.get("minOrderQuantity") or 1),
                    cgst=Decimal(str(v.get("cgst") or 0)),
                    sgst=Decimal(str(v.get("sgst") or 0)),
                )
                db.add(new_variant)
            db.commit()
    
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
    request: Request,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    categoryId: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    divisionId: Optional[str] = Form(None),
    division_id: Optional[str] = Form(None),
    brand_id: Optional[str] = Form(None),
    brandId: Optional[str] = Form(None),
    company_id: Optional[str] = Form(None),
    companyId: Optional[str] = Form(None),
    mrp: Optional[Decimal] = Form(None),
    sellingPrice: Optional[Decimal] = Form(None),
    selling_price: Optional[Decimal] = Form(None),
    commissionCost: Optional[Decimal] = Form(None),
    commission_cost: Optional[Decimal] = Form(None),
    stockQuantity: Optional[int] = Form(None),
    stock_quantity: Optional[int] = Form(None),
    minOrderQuantity: Optional[int] = Form(None),
    min_order_quantity: Optional[int] = Form(None),
    unit: Optional[str] = Form(None),
    piecesPerSet: Optional[int] = Form(None),
    pieces_per_set: Optional[int] = Form(None),
    isFeatured: Optional[str] = Form(None),
    is_featured: Optional[str] = Form(None),
    isAvailable: Optional[str] = Form(None),
    is_available: Optional[str] = Form(None),
    expiryDate: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    hsnCode: Optional[str] = Form(None),
    hsn_code: Optional[str] = Form(None),
    manufacturerName: Optional[str] = Form(None),
    manufacturerAddress: Optional[str] = Form(None),
    cancelPolicy: Optional[str] = Form(None),
    returnPolicy: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    metaTitle: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    metaDescription: Optional[str] = Form(None),
    variants: Optional[str] = Form(None),
    images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    primaryIndex: Optional[int] = Form(None),
    primary_index: Optional[int] = Form(None),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Update a product. Accepts multipart/form-data identical to the create endpoint.
    Sellers can only update products they created.
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not check_seller_product_access(seller, product):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update products created by you."
        )

    # Normalize camelCase / snake_case aliases
    resolved_category_id = categoryId or category_id
    resolved_division_id = divisionId or division_id
    resolved_brand_id = brand_id or brandId
    resolved_company_id = company_id or companyId
    resolved_selling_price = sellingPrice if sellingPrice is not None else selling_price
    resolved_commission_cost = commissionCost if commissionCost is not None else commission_cost
    resolved_stock = stockQuantity if stockQuantity is not None else stock_quantity
    resolved_moq = minOrderQuantity if minOrderQuantity is not None else min_order_quantity
    resolved_pps = piecesPerSet if piecesPerSet is not None else pieces_per_set
    resolved_is_featured = isFeatured if isFeatured is not None else is_featured
    resolved_is_available = isAvailable if isAvailable is not None else is_available
    resolved_expiry = expiryDate or expiry_date
    resolved_meta_title = meta_title or metaTitle
    resolved_meta_description = meta_description or metaDescription
    resolved_primary_index = primaryIndex if primaryIndex is not None else primary_index

    # Apply scalar field updates
    if name is not None:
        product.name = name
        # Only update slug when the name actually changes, and avoid conflicts
        new_slug = generate_slug(name)
        if new_slug != product.slug:
            existing_slugs = [
                row[0]
                for row in db.query(Product.slug)
                .filter(Product.id != product_id)
                .all()
            ]
            product.slug = make_unique_slug(new_slug, existing_slugs)

    if description is not None:
        product.description = description

    if resolved_category_id:
        try:
            UUID(resolved_category_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category ID format")
        category = db.query(Category).filter(Category.id == resolved_category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        product.category_id = resolved_category_id

    if resolved_division_id is not None:
        if resolved_division_id:
            try:
                UUID(resolved_division_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid division ID format")
        product.division_id = resolved_division_id or None

    if resolved_brand_id is not None:
        if resolved_brand_id:
            try:
                UUID(resolved_brand_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid brand ID format")
        product.brand_id = resolved_brand_id or None

    if resolved_company_id is not None:
        if resolved_company_id:
            try:
                UUID(resolved_company_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid company ID format")
        product.company_id = resolved_company_id or None

    if mrp is not None:
        product.mrp = mrp

    if resolved_selling_price is not None:
        product.selling_price = resolved_selling_price

    if resolved_commission_cost is not None:
        product.commission_cost = resolved_commission_cost

    if resolved_stock is not None:
        product.stock_quantity = int(resolved_stock)

    if resolved_moq is not None:
        product.min_order_quantity = int(resolved_moq)

    if unit is not None:
        product.unit = unit
        product.pieces_per_set = _normalize_pieces_per_set(unit, resolved_pps)
    elif resolved_pps is not None:
        product.pieces_per_set = _normalize_pieces_per_set(product.unit, resolved_pps)

    if resolved_is_featured is not None:
        product.is_featured = str(resolved_is_featured).lower() in ("true", "1", "yes")

    if resolved_is_available is not None:
        product.is_available = str(resolved_is_available).lower() in ("true", "1", "yes")

    if resolved_expiry is not None:
        product.expiry_date = date.fromisoformat(resolved_expiry.strip()) if resolved_expiry.strip() else None

    if resolved_meta_title is not None:
        product.meta_title = resolved_meta_title

    if resolved_meta_description is not None:
        product.meta_description = resolved_meta_description

    resolved_hsn = hsnCode if hsnCode is not None else hsn_code
    if resolved_hsn is not None:
        product.hsn_code = resolved_hsn or None

    if manufacturerName is not None:
        product.manufacturer_name = manufacturerName or None

    if manufacturerAddress is not None:
        product.manufacturer_address = manufacturerAddress or None

    if cancelPolicy is not None:
        product.cancel_policy = cancelPolicy or None

    if returnPolicy is not None:
        product.return_policy = returnPolicy or None

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not save product: {e.orig}")

    # Handle image uploads
    if images is not None:
        image_files: List[UploadFile] = images if isinstance(images, list) else [images]
        for idx, image in enumerate(image_files):
            try:
                image_url = save_uploaded_file(image, "product", product.id, request)
                product_image = ProductImage(
                    product_id=product.id,
                    image_url=image_url,
                    display_order=idx,
                    is_primary=(resolved_primary_index is not None and idx == int(resolved_primary_index)),
                )
                db.add(product_image)
            except Exception:
                continue
        db.commit()

    # Handle variants (upsert by id when provided, create new otherwise)
    if variants:
        try:
            variants_list = json.loads(variants) if isinstance(variants, str) else variants
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid JSON in variants field")
        if isinstance(variants_list, list):
            for v in variants_list:
                variant_id = v.get("id")
                existing = db.query(ProductVariant).filter(
                    ProductVariant.id == str(variant_id),
                    ProductVariant.product_id == str(product.id)
                ).first() if variant_id else None

                ptype = normalize_packaging_label_type(v.get("packagingLabelType") or "")
                if existing:
                    existing.hsn_code = v.get("hsnCode") or existing.hsn_code
                    # Only overwrite packaging_label_type when the incoming value is non-null
                    if ptype is not None:
                        existing.packaging_label_type = ptype
                    existing.set_pcs = v.get("setPieces") or existing.set_pcs
                    existing.weight = v.get("weight") or existing.weight
                    existing.mrp = Decimal(str(v["mrp"])) if v.get("mrp") is not None else existing.mrp
                    existing.special_price = Decimal(str(v["specialPrice"])) if v.get("specialPrice") is not None else existing.special_price
                    existing.free_item = v.get("freeItem") or existing.free_item
                    existing.min_order_quantity = int(v.get("minOrderQuantity") or 1)
                    existing.cgst = Decimal(str(v.get("cgst") or 0))
                    existing.sgst = Decimal(str(v.get("sgst") or 0))
                else:
                    new_variant = ProductVariant(
                        product_id=str(product.id),
                        hsn_code=v.get("hsnCode") or "",
                        packaging_label_type=ptype,
                        set_pcs=v.get("setPieces") or "",
                        weight=v.get("weight") or "",
                        mrp=Decimal(str(v.get("mrp") or 0)),
                        special_price=Decimal(str(v.get("specialPrice") or 0)),
                        free_item=v.get("freeItem") or "",
                        min_order_quantity=int(v.get("minOrderQuantity") or 1),
                        cgst=Decimal(str(v.get("cgst") or 0)),
                        sgst=Decimal(str(v.get("sgst") or 0)),
                    )
                    db.add(new_variant)
            try:
                db.commit()
            except IntegrityError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Could not save variants: {e.orig}")

    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_updated",
        entity_type="product",
        entity_id=UUID(str(product.id)),
        details={"product_name": product.name},
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
            detail="Access denied. You can only delete products created by you."
        )
    
    product_name = product.name
    product_uuid = UUID(str(product.id))

    db.delete(product)
    db.commit()

    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_deleted",
        entity_type="product",
        entity_id=product_uuid,
        details={"product_name": product_name},
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
    
    # Sellers can only see products created by them
    if seller.role == AdminRole.SELLER:
        query = query.filter(Product.created_by == str(seller.id))
    
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
    Sellers can select any company when creating products.
    """

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


# ── Service Area (location-based visibility) ─────────────────────────────────

@router.get("/{product_id}/service-area", response_model=ResponseModel)
async def get_seller_product_service_area(
    product_id: str,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db),
):
    """
    Get serviceable pincodes for a product.
    Sellers can only view service areas for their own products.
    An empty list means no restriction (available platform-wide).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not check_seller_product_access(seller, product):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage products created by you.")

    areas = db.query(ProductServiceArea).filter(ProductServiceArea.product_id == product_id).all()
    return ResponseModel(
        success=True,
        data={
            "productId": product_id,
            "productName": product.name,
            "serviceAreas": [
                {"pincode": a.pincode, "city": a.city, "state": a.state}
                for a in areas
            ],
            "isRestricted": len(areas) > 0,
        },
        message="Service area retrieved successfully",
    )


@router.put("/{product_id}/service-area", response_model=ResponseModel)
async def update_seller_product_service_area(
    product_id: str,
    request: Request,
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db),
):
    """
    Replace serviceable pincodes for a product.
    Sellers can only update service areas for their own products.

    Body:
    {
        "pincodes": [
            {"pincode": "500001", "city": "Hyderabad", "state": "Telangana"}
        ]
    }

    Send `"pincodes": []` to remove all restrictions (platform-wide delivery).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not check_seller_product_access(seller, product):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage products created by you.")

    body = await request.json()
    pincodes = body.get("pincodes", [])

    if not isinstance(pincodes, list):
        raise HTTPException(status_code=400, detail="'pincodes' must be a list")

    seen = set()
    for entry in pincodes:
        if not isinstance(entry, dict) or "pincode" not in entry:
            raise HTTPException(status_code=400, detail="Each entry must have a 'pincode' field")
        pc = str(entry["pincode"]).strip()
        if not pc:
            raise HTTPException(status_code=400, detail="Pincode cannot be empty")
        if pc in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate pincode: {pc}")
        seen.add(pc)

    db.query(ProductServiceArea).filter(ProductServiceArea.product_id == product_id).delete()

    new_areas = []
    for entry in pincodes:
        area = ProductServiceArea(
            product_id=product_id,
            pincode=str(entry["pincode"]).strip(),
            city=(entry.get("city") or "").strip() or None,
            state=(entry.get("state") or "").strip() or None,
        )
        db.add(area)
        new_areas.append(area)

    db.commit()

    log_admin_activity(
        db=db,
        admin_id=seller.id,
        action="product_service_area_updated",
        entity_type="product",
        entity_id=UUID(str(product.id)),
        details={"pincode_count": len(new_areas)},
        request=request,
    )

    return ResponseModel(
        success=True,
        data={
            "productId": product_id,
            "serviceAreas": [
                {"pincode": a.pincode, "city": a.city, "state": a.state}
                for a in new_areas
            ],
            "isRestricted": len(new_areas) > 0,
        },
        message="Service area updated successfully",
    )
