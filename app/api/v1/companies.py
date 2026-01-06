from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.company import CompanyResponse, BrandResponse
from app.schemas.common import ResponseModel
from app.models.company import Company
from app.models.product import Product
from app.models.category import Category
from app.utils.pagination import paginate
from typing import Optional
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all companies"""
    query = db.query(Company)
    total = query.count()
    offset = (page - 1) * limit
    companies = query.offset(offset).limit(limit).all()
    
    # Format companies with logoUrl
    company_list = []
    for c in companies:
        company_data = {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "logoUrl": c.logo_url or c.logo,
            "createdAt": c.created_at.isoformat() if c.created_at else None
        }
        company_list.append(company_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": company_list,
            "pagination": paginate(companies, page, limit, total)
        }
    )


@router.get("/{company_id}", response_model=ResponseModel)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    """Get company details"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get unique brands for this company
    brands = db.query(Product.brand).filter(
        Product.company_id == company_id
    ).distinct().all()
    
    brand_list = [{"name": b[0], "count": db.query(Product).filter(
        Product.company_id == company_id,
        Product.brand == b[0]
    ).count()} for b in brands]
    
    company_data = CompanyResponse.model_validate(company)
    return ResponseModel(
        success=True,
        data={
            **company_data.dict(),
            "brands": brand_list
        }
    )


@router.get("/hul/brands", response_model=ResponseModel)
def get_hul_brands(
    category: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get HUL brands"""
    hul = db.query(Company).filter(Company.name.ilike("%HUL%")).first()
    if not hul:
        return ResponseModel(success=True, data=[])
    
    query = db.query(Product.brand).filter(Product.company_id == hul.id)
    if category:
        query = query.filter(Product.category_id == category)
    
    brands = query.distinct().all()
    brand_list = [{"name": b[0], "count": db.query(Product).filter(
        Product.company_id == hul.id,
        Product.brand == b[0]
    ).count()} for b in brands]
    
    return ResponseModel(success=True, data=brand_list)


@router.get("/brands/biscuits", response_model=ResponseModel)
def get_biscuit_brands(db: Session = Depends(get_db)):
    """Get biscuit brands"""
    # Assuming there's a category named "Biscuits" or similar
    biscuit_category = db.query(Category).filter(
        Category.name.ilike("%biscuit%")
    ).first()
    
    if not biscuit_category:
        return ResponseModel(success=True, data=[])
    
    brands = db.query(Product.brand).filter(
        Product.category_id == biscuit_category.id
    ).distinct().all()
    
    brand_list = [{"name": b[0], "count": db.query(Product).filter(
        Product.category_id == biscuit_category.id,
        Product.brand == b[0]
    ).count()} for b in brands]
    
    return ResponseModel(success=True, data=brand_list)

