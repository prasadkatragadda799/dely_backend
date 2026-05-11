from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, false
from app.database import get_db
from app.api.deps import get_current_user, require_kyc_verified
from app.schemas.product import ProductResponse, ProductListResponse
from app.schemas.common import ResponseModel, PaginatedResponse, PaginationModel
from app.models.product import Product
from app.models.product_service_area import ProductServiceArea
from app.models.company import Company
from app.models.category import Category
from app.models.division import Division
from app.utils.pagination import paginate
from app.utils.discount import calculate_discount_percentage
from app.utils.product_pricing import build_price_options_for_api
from app.utils.packaging_label import variant_row_for_public_api
from typing import Optional
from decimal import Decimal
from uuid import UUID

router = APIRouter()


def _resolve_division_id(db: Session, division_slug: Optional[str]):
    """
    Resolve division id by slug.

    Note: your DB seeds a "Default grocery division" as an actual row
    (`divisions.slug='default'`, `id=00000000-0000-0000-0000-000000000001`).
    So we should not assume default division == `division_id == NULL`.
    """
    # When frontend omits `division_slug`, treat it as "default grocery".
    # Your DB seeds this as a *row* (not necessarily `division_id IS NULL`),
    # so we try multiple identifiers to find it.
    default_like_slugs = {"default", "grocery"}

    if not division_slug or division_slug in default_like_slugs:
        d = (
            db.query(Division)
            .filter(
                Division.is_active == True,
                or_(Division.slug.in_(list(default_like_slugs)), Division.name == "Grocery"),
            )
            .first()
        )
        # If there is no exact name match, try a looser fallback.
        if not d:
            d = (
                db.query(Division)
                .filter(Division.is_active == True, Division.name.ilike("%grocery%"))
                .first()
            )
        return str(d.id) if d else None

    # For non-default division slugs, resolve by slug.
    d = (
        db.query(Division)
        .filter(Division.slug == division_slug, Division.is_active == True)
        .first()
    )
    return str(d.id) if d else None


@router.get("", response_model=ResponseModel)
def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    company: Optional[UUID] = None,
    brand: Optional[UUID] = None,
    division_slug: Optional[str] = Query(None, description="Filter by division, e.g. 'kitchen'. Omit for default Grocery."),
    search: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sort: Optional[str] = Query("created_at", pattern="^(price_asc|price_desc|name|popularity|created_at)$"),
    featured: Optional[bool] = None,
    pincode: Optional[str] = Query(None, description="Customer's delivery pincode — filters out products not serviceable there."),
    current_user = Depends(require_kyc_verified),
    db: Session = Depends(get_db)
):
    """Get all products with filters (Mobile App API) - Requires KYC verification"""
    query = db.query(Product).filter(Product.is_available == True)
    effective_selling_price = Product.selling_price + func.coalesce(Product.commission_cost, 0)

    # Division filter (e.g. Kitchen)
    #
    # Legacy behavior assumed "default division" == `division_id IS NULL`.
    # Current seeded data uses an actual division row with slug `default`.
    if division_slug is None or division_slug == "default":
        default_division_id = _resolve_division_id(db, "default")
        if default_division_id:
            # Include both:
            # - legacy products stored with NULL division_id
            # - new products stored against the seeded "default" division row
            query = query.filter(
                or_(Product.division_id == None, Product.division_id == default_division_id)
            )
        else:
            query = query.filter(Product.division_id == None)
    else:
        division_id = _resolve_division_id(db, division_slug)
        if division_id is not None:
            query = query.filter(Product.division_id == division_id)
        else:
            # Unknown division_slug: return empty rather than falling back to default
            # grocery, which would cause FMCG products to bleed into other divisions.
            query = query.filter(false())

    # Apply filters (convert UUIDs to strings for database queries)
    if category:
        category_id_str = str(category)
        # Get products from this category and all subcategories
        from app.models.category import Category
        category_ids = [category_id_str]
        subcategories = db.query(Category).filter(Category.parent_id == category_id_str).all()
        category_ids.extend([str(c.id) for c in subcategories])
        query = query.filter(Product.category_id.in_(category_ids))
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
        query = query.filter(effective_selling_price >= min_price)
    if max_price:
        query = query.filter(effective_selling_price <= max_price)
    if featured is not None:
        query = query.filter(Product.is_featured == featured)
    if pincode:
        # Keep products that have NO service-area rows (unrestricted) OR have a row matching this pincode
        has_any_restriction = (
            db.query(ProductServiceArea.product_id)
            .filter(ProductServiceArea.product_id == Product.id)
            .correlate(Product)
            .exists()
        )
        pincode_matches = (
            db.query(ProductServiceArea.product_id)
            .filter(
                ProductServiceArea.product_id == Product.id,
                ProductServiceArea.pincode == pincode.strip(),
            )
            .correlate(Product)
            .exists()
        )
        query = query.filter(or_(~has_any_restriction, pincode_matches))

    # Apply sorting
    if sort == "price_asc":
        order_by = effective_selling_price.asc()
    elif sort == "price_desc":
        order_by = effective_selling_price.desc()
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
    products = (
        query.options(
            joinedload(Product.category),
            joinedload(Product.division),
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.variants),
            joinedload(Product.product_images),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Format products with enhanced data
    product_list = []
    for p in products:
        # Calculate discount percentage using effective selling price.
        effective_price = (p.selling_price or 0) + (p.commission_cost or 0)
        discount = 0.0
        if p.mrp and p.mrp > 0:
            discount = float(((p.mrp - effective_price) / p.mrp) * 100)
        
        product_data = {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "mrp": float(p.mrp) if p.mrp else None,
            "sellingPrice": float(effective_price) if effective_price is not None else None,
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
            product_data["variants"] = []
            for v in p.variants:
                variant_mrp = v.mrp
                variant_price = getattr(v, "special_price", None) or variant_mrp
                variant_discount = calculate_discount_percentage(variant_mrp, variant_price)
                
                product_data["variants"].append(
                    variant_row_for_public_api(v, variant_mrp, variant_price, variant_discount)
                )
        else:
            product_data["variants"] = []

        product_data["priceOptions"] = build_price_options_for_api(p)

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

        if p.division:
            product_data["divisionSlug"] = p.division.slug

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
def get_product(
    product_id: UUID,
    current_user = Depends(require_kyc_verified),
    db: Session = Depends(get_db)
):
    """Get product details by ID (Mobile App API) - Requires KYC verification"""
    product = (
        db.query(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.division),
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.variants),
            joinedload(Product.product_images),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=404, detail="Product not available")
    
    # Calculate discount using effective selling price
    effective_price = (product.selling_price or 0) + (product.commission_cost or 0)
    discount = 0.0
    if product.mrp and product.mrp > 0:
        discount = float(((product.mrp - effective_price) / product.mrp) * 100)
    
    product_data = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "mrp": float(product.mrp) if product.mrp else None,
        "sellingPrice": float(effective_price) if effective_price is not None else None,
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
        product_data["variants"] = []
        for v in product.variants:
            variant_mrp = v.mrp
            variant_price = getattr(v, "special_price", None) or variant_mrp
            variant_discount = calculate_discount_percentage(variant_mrp, variant_price)
            
            product_data["variants"].append(
                variant_row_for_public_api(v, variant_mrp, variant_price, variant_discount)
            )
    else:
        product_data["variants"] = []

    product_data["priceOptions"] = build_price_options_for_api(product)

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

    if product.division:
        product_data["divisionSlug"] = product.division.slug

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
def get_product_by_slug(
    slug: str,
    current_user = Depends(require_kyc_verified),
    db: Session = Depends(get_db)
):
    """Get product details by slug (Mobile App API) - Requires KYC verification"""
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.is_available:
        raise HTTPException(status_code=404, detail="Product not available")
    
    # Use same formatting as get_product
    effective_price = (product.selling_price or 0) + (product.commission_cost or 0)
    discount = 0.0
    if product.mrp and product.mrp > 0:
        discount = float(((product.mrp - effective_price) / product.mrp) * 100)
    
    product_data = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "mrp": float(product.mrp) if product.mrp else None,
        "sellingPrice": float(effective_price) if effective_price is not None else None,
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
    current_user = Depends(require_kyc_verified),
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
        category_id_str = str(category)
        # Get products from this category and all subcategories
        category_ids = [category_id_str]
        subcategories = db.query(Category).filter(Category.parent_id == category_id_str).all()
        category_ids.extend([str(c.id) for c in subcategories])
        query = query.filter(Product.category_id.in_(category_ids))
    if company:
        query = query.filter(Product.company_id == str(company))
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
    current_user = Depends(require_kyc_verified),
    db: Session = Depends(get_db)
):
    """Get featured products - Requires KYC verification"""
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
            "variants": [],
            "createdAt": p.created_at.isoformat() if p.created_at else None
        }
        
        # Add variants with discount calculation
        if hasattr(p, "variants") and p.variants:
            for v in p.variants:
                variant_mrp = getattr(v, "mrp", None)
                variant_price = getattr(v, "special_price", None) or variant_mrp
                variant_discount = calculate_discount_percentage(variant_mrp, variant_price)
                
                product_data["variants"].append(
                    variant_row_for_public_api(v, variant_mrp, variant_price, variant_discount)
                )
        
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
    current_user = Depends(require_kyc_verified),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get products by company name"""
    company = db.query(Company).filter(Company.name.ilike(f"%{company_name}%")).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(Product).filter(Product.company_id == str(company.id))
    if category:
        category_id_str = str(category)
        # Get products from this category and all subcategories
        category_ids = [category_id_str]
        subcategories = db.query(Category).filter(Category.parent_id == category_id_str).all()
        category_ids.extend([str(c.id) for c in subcategories])
        query = query.filter(Product.category_id.in_(category_ids))
    
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
    current_user = Depends(require_kyc_verified),
    db: Session = Depends(get_db)
):
    """Get products by brand name - Requires KYC verification"""
    query = db.query(Product).filter(Product.brand.ilike(f"%{brand_name}%"))
    if category:
        category_id_str = str(category)
        # Get products from this category and all subcategories
        category_ids = [category_id_str]
        subcategories = db.query(Category).filter(Category.parent_id == category_id_str).all()
        category_ids.extend([str(c.id) for c in subcategories])
        query = query.filter(Product.category_id.in_(category_ids))
    
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

