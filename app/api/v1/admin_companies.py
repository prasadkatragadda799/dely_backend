"""
Admin Companies & Brands Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
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
from app.models.admin import Admin

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
        product_count = db.query(func.count(Product.id)).filter(
            Product.company_id == company.id
        ).scalar() or 0
        
        # Get brand count
        brand_count = db.query(func.count(Brand.id)).filter(
            Brand.company_id == company.id
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
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get counts
    product_count = db.query(func.count(Product.id)).filter(
        Product.company_id == company.id
    ).scalar() or 0
    
    brand_count = db.query(func.count(Brand.id)).filter(
        Brand.company_id == company.id
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
    company_data: AdminCompanyCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new company"""
    # Check if company with same name exists
    existing = db.query(Company).filter(Company.name == company_data.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Company with this name already exists"
        )
    
    company = Company(
        name=company_data.name,
        description=company_data.description,
        logo_url=company_data.logo_url
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="company_created",
        entity_type="company",
        entity_id=company.id,
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
    company = db.query(Company).filter(Company.id == company_id).first()
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
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="company_updated",
        entity_type="company",
        entity_id=company_id,
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
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_name = company.name
    db.delete(company)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="company_deleted",
        entity_type="company",
        entity_id=company_id,
        details={"name": company_name},
        request=request
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
        query = query.filter(Brand.company_id == company_id)
    
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
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
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
    brand_data: AdminBrandCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new brand"""
    brand = Brand(
        name=brand_data.name,
        company_id=brand_data.company_id,
        category_id=brand_data.category_id,
        logo_url=brand_data.logo_url
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
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
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
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
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

