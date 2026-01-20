"""
Seller Resources Endpoints
Provides access to brands, categories, and companies for sellers
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.admin import Admin, AdminRole
from app.models.brand import Brand
from app.models.category import Category
from app.models.company import Company
from app.api.admin_deps import require_seller_or_above

router = APIRouter()


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
    
    # Get all brands
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
