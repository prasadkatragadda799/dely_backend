"""
Admin Companies & Brands Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.schemas.admin_company import (
    AdminCompanyCreate, AdminCompanyUpdate, AdminCompanyResponse,
    AdminBrandCreate, AdminBrandUpdate, AdminBrandResponse
)
from app.schemas.common import ResponseModel
from app.models.company import Company
from app.models.brand import Brand
from app.models.product import Product
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.api.v1.admin_upload import save_uploaded_file
from app.models.admin import Admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Companies ==========

@router.get("/companies", response_model=ResponseModel)
async def list_companies(
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all companies with product and brand counts"""
    companies = db.query(Company).all()
    
    company_list = []
    for company in companies:
        # Get product count
        # Product.company_id is UUID type in model, but DB has String(36)
        # Use cast to handle type mismatch
        product_count = db.query(func.count(Product.id)).filter(
            cast(Product.company_id, String) == str(company.id)
        ).scalar() or 0
        
        # Get brand count (Brand.company_id is already String(36))
        brand_count = db.query(func.count(Brand.id)).filter(
            Brand.company_id == str(company.id)
        ).scalar() or 0
        
        company_list.append({
            "id": company.id,
            "name": company.name,
            "description": company.description,
            "logoUrl": company.logo_url or company.logo,  # Support legacy field
            "totalProducts": product_count,
            "totalBrands": brand_count,
            "createdAt": company.created_at,
            "updatedAt": company.updated_at
        })
    
    return ResponseModel(
        success=True,
        data=company_list,
        message="Companies retrieved successfully"
    )


@router.get("/companies/{company_id}", response_model=ResponseModel)
async def get_company(
    company_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get company details"""
    # Convert UUID to string for database query (Company.id is String(36))
    # Database may store UUIDs with or without dashes, so try both formats
    company_id_str = str(company_id).strip()
    company_id_no_dashes = company_id_str.replace('-', '')
    
    # Try with dashes first (in case database has dashes)
    company = db.query(Company).filter(Company.id == company_id_str).first()
    
    # If not found, try without dashes
    if not company:
        company = db.query(Company).filter(Company.id == company_id_no_dashes).first()
    
    if not company:
        # Log for debugging - check what IDs actually exist
        all_companies = db.query(Company.id, Company.name).all()
        logger.warning(f"Company not found with ID: {company_id_str} (also tried: {company_id_no_dashes})")
        logger.debug(f"Available companies: {[(str(c.id), c.name) for c in all_companies[:5]]}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get counts
    # Product.company_id is UUID type in model, but DB has String(36)
    # Use cast to handle type mismatch
    product_count = db.query(func.count(Product.id)).filter(
        cast(Product.company_id, String) == str(company.id)
    ).scalar() or 0
    
    # Brand.company_id is already String(36)
    brand_count = db.query(func.count(Brand.id)).filter(
        Brand.company_id == str(company.id)
    ).scalar() or 0
    
    company_data = {
        "id": company.id,
        "name": company.name,
        "description": company.description,
        "logoUrl": company.logo_url or company.logo,
        "totalProducts": product_count,
        "totalBrands": brand_count,
        "createdAt": company.created_at,
        "updatedAt": company.updated_at
    }
    
    return ResponseModel(
        success=True,
        data=company_data,
        message="Company retrieved successfully"
    )


@router.post("/companies", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_company(
    request: Request,
    # Form fields
    name: str = Form(...),
    description: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),  # Logo file upload
    logoUrl: Optional[str] = Form(None),  # Or provide URL directly
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new company with form data and optional logo upload"""
    # Check if company with same name exists (case-insensitive, trimmed)
    name_trimmed = name.strip()
    existing = db.query(Company).filter(
        func.lower(Company.name) == func.lower(name_trimmed)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Company with this name already exists: {existing.name}"
        )
    
    # Handle logo upload
    logo_url = logoUrl
    if logo and logo.filename:
        try:
            # Save uploaded logo file
            logo_url = save_uploaded_file(logo, "company", None, request)
        except Exception as e:
            logger.error(f"Error uploading company logo: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error uploading logo: {str(e)}"
            )
    
    company = Company(
        name=name,
        description=description,
        logo_url=logo_url
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    # Log activity
    # Convert company.id (String) to UUID for entity_id
    try:
        entity_id_uuid = UUID(company.id) if company.id else None
    except (ValueError, AttributeError):
        entity_id_uuid = None
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="company_created",
        entity_type="company",
        entity_id=entity_id_uuid,
        details={"name": company.name},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminCompanyResponse.model_validate(company),
        message="Company created successfully"
    )


@router.put("/companies/{company_id}", response_model=ResponseModel)
async def update_company(
    company_id: UUID,
    company_data: AdminCompanyUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update a company"""
    # Convert UUID to string for database query (Company.id is String(36))
    # Database may store UUIDs with or without dashes, so try both formats
    company_id_str = str(company_id).strip()
    company_id_no_dashes = company_id_str.replace('-', '')
    
    # Try with dashes first (in case database has dashes)
    company = db.query(Company).filter(Company.id == company_id_str).first()
    
    # If not found, try without dashes
    if not company:
        company = db.query(Company).filter(Company.id == company_id_no_dashes).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check name uniqueness if name is being updated
    if company_data.name and company_data.name != company.name:
        existing = db.query(Company).filter(
            Company.name == company_data.name,
            Company.id != company_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Company with this name already exists"
            )
    
    # Update fields
    update_data = company_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(company, key):
            setattr(company, key, value)
    
    db.commit()
    db.refresh(company)
    
    # Log activity
    # company_id is already a UUID, so we can use it directly
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="company_updated",
        entity_type="company",
        entity_id=company_id,  # This is already a UUID from the path parameter
        details=update_data,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminCompanyResponse.model_validate(company),
        message="Company updated successfully"
    )


@router.delete("/companies/{company_id}", response_model=ResponseModel)
async def delete_company(
    company_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete a company"""
    try:
        # Convert UUID to string for database query (Company.id is String(36))
        # Database may store UUIDs with or without dashes, so try both formats
        company_id_str = str(company_id).strip()
        company_id_no_dashes = company_id_str.replace('-', '')
        
        # Try with dashes first (in case database has dashes)
        company = db.query(Company).filter(Company.id == company_id_str).first()
        
        # If not found, try without dashes
        if not company:
            company = db.query(Company).filter(Company.id == company_id_no_dashes).first()
        
        if not company:
            # Log for debugging
            all_companies = db.query(Company.id, Company.name).all()
            logger.warning(f"Company not found with ID: {company_id_str} (also tried: {company_id_no_dashes})")
            logger.debug(f"Available companies: {[(str(c.id), c.name) for c in all_companies[:5]]}")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Use the actual company ID from the database for consistency
        actual_company_id = str(company.id)
        
        # Check if company has products (prevent deletion if it does)
        # Use text() for raw SQL comparison to handle type mismatch
        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM products WHERE company_id = :company_id"),
            {"company_id": actual_company_id}
        )
        product_count = result.scalar() or 0
        
        if product_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete company. It has {product_count} associated product(s). Please remove or reassign products first."
            )
        
        # Check if company has brands (use actual company ID from database)
        brand_count = db.query(Brand).filter(Brand.company_id == actual_company_id).count()
        if brand_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete company. It has {brand_count} associated brand(s). Please remove or reassign brands first."
            )
        
        # Note: offers table doesn't have company_id column in the database,
        # so we can't check for associated offers. The relationship exists in the model
        # but the database schema doesn't support it yet.
        
        company_name = company.name
        db.delete(company)
        db.commit()
        
        # Log activity
        try:
            # Convert company_id_str (String) to UUID for entity_id
            try:
                entity_id_uuid = UUID(company_id_str) if company_id_str else None
            except (ValueError, AttributeError):
                # If company_id is not a valid UUID format, try without dashes
                try:
                    entity_id_uuid = UUID(company_id_str.replace('-', '')) if company_id_str else None
                except (ValueError, AttributeError):
                    entity_id_uuid = None
            
            log_admin_activity(
                db=db,
                admin_id=admin.id,
                action="company_deleted",
                entity_type="company",
                entity_id=entity_id_uuid,
                details={"name": company_name},
                request=request
            )
        except Exception as log_error:
            # Don't fail the deletion if logging fails
            logger.error(f"Error logging company deletion: {str(log_error)}")
        
        return ResponseModel(
            success=True,
            message="Company deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting company: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting company: {str(e)}"
        )
    
    return ResponseModel(
        success=True,
        message="Company deleted successfully"
    )


# ========== Brands ==========

@router.get("/brands", response_model=ResponseModel)
async def list_brands(
    company_id: Optional[UUID] = Query(None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all brands, optionally filtered by company"""
    query = db.query(Brand)
    
    if company_id:
        # Convert UUID to string for database query (Brand.company_id is String(36))
        query = query.filter(Brand.company_id == str(company_id))
    
    brands = query.all()
    
    brand_list = []
    for brand in brands:
        brand_data = {
            "id": brand.id,
            "name": brand.name,
            "logoUrl": brand.logo_url,
            "createdAt": brand.created_at,
            "updatedAt": brand.updated_at
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


@router.get("/brands/{brand_id}", response_model=ResponseModel)
async def get_brand(
    brand_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get brand details"""
    # Convert UUID to string for database query (Brand.id is String(36))
    # Database stores UUIDs WITHOUT dashes, so remove dashes from UUID
    brand_id_str = str(brand_id).replace('-', '').strip()
    brand = db.query(Brand).filter(Brand.id == brand_id_str).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand_data = AdminBrandResponse.model_validate(brand)
    if brand.company:
        brand_data.company = {"id": brand.company.id, "name": brand.company.name}
    if brand.category:
        brand_data.category = {"id": brand.category.id, "name": brand.category.name}
    
    return ResponseModel(
        success=True,
        data=brand_data,
        message="Brand retrieved successfully"
    )


@router.post("/brands", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_brand(
    request: Request,
    # Form fields
    name: str = Form(...),
    companyId: Optional[str] = Form(None),  # Frontend sends as companyId
    categoryId: Optional[str] = Form(None),  # Frontend sends as categoryId
    logo: Optional[UploadFile] = File(None),  # Logo file upload
    logoUrl: Optional[str] = Form(None),  # Or provide URL directly
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new brand with form data and optional logo upload"""
    # Validate UUID format but keep as strings (database uses String(36))
    company_id_str = None
    if companyId:
        try:
            # Validate UUID format but keep as string
            UUID(companyId)  # Just for validation
            company_id_str = companyId
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company ID format"
            )
    
    category_id_str = None
    if categoryId:
        try:
            # Validate UUID format but keep as string
            UUID(categoryId)  # Just for validation
            category_id_str = categoryId
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format"
            )
    
    # Handle logo upload
    logo_url = logoUrl
    if logo and logo.filename:
        try:
            # Save uploaded logo file
            logo_url = save_uploaded_file(logo, "brand", None, request)
        except Exception as e:
            logger.error(f"Error uploading brand logo: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error uploading logo: {str(e)}"
            )
    
    brand = Brand(
        name=name,
        company_id=company_id_str,  # String(36), not UUID
        category_id=category_id_str,  # String(36), not UUID
        logo_url=logo_url
    )
    
    db.add(brand)
    db.commit()
    db.refresh(brand)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="brand_created",
        entity_type="brand",
        entity_id=brand.id,
        details={"name": brand.name},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminBrandResponse.model_validate(brand),
        message="Brand created successfully"
    )


@router.put("/brands/{brand_id}", response_model=ResponseModel)
async def update_brand(
    brand_id: UUID,
    brand_data: AdminBrandUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update a brand"""
    # Convert UUID to string for database query (Brand.id is String(36))
    # Database stores UUIDs WITHOUT dashes, so remove dashes from UUID
    brand_id_str = str(brand_id).replace('-', '').strip()
    brand = db.query(Brand).filter(Brand.id == brand_id_str).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Update fields
    update_data = brand_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(brand, key):
            setattr(brand, key, value)
    
    db.commit()
    db.refresh(brand)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="brand_updated",
        entity_type="brand",
        entity_id=brand_id,
        details=update_data,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminBrandResponse.model_validate(brand),
        message="Brand updated successfully"
    )


@router.delete("/brands/{brand_id}", response_model=ResponseModel)
async def delete_brand(
    brand_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete a brand"""
    # Convert UUID to string for database query (Brand.id is String(36))
    # Database stores UUIDs WITHOUT dashes, so remove dashes from UUID
    brand_id_str = str(brand_id).replace('-', '').strip()
    brand = db.query(Brand).filter(Brand.id == brand_id_str).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand_name = brand.name
    db.delete(brand)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="brand_deleted",
        entity_type="brand",
        entity_id=brand_id,
        details={"name": brand_name},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Brand deleted successfully"
    )

