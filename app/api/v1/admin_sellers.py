"""
Admin Seller Management Endpoints
Admins can create and manage sellers who can add their own products
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.admin import Admin, AdminRole
from app.models.company import Company
from app.api.admin_deps import require_admin_or_super_admin, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.security import get_password_hash
import secrets

router = APIRouter()


class CreateSellerRequest(BaseModel):
    """Request model for creating a seller"""
    email: EmailStr
    name: str
    password: Optional[str] = None  # If not provided, auto-generate
    company_id: str  # UUID of the company this seller belongs to


class UpdateSellerRequest(BaseModel):
    """Request model for updating a seller"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_seller(
    seller_data: CreateSellerRequest,
    request: Request,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new seller account.
    Sellers can only manage products for their assigned company.
    Only admins and super admins can create sellers.
    """
    # Check if email already exists
    existing_admin = db.query(Admin).filter(Admin.email == seller_data.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify company exists
    company = db.query(Company).filter(Company.id == seller_data.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Generate password if not provided
    password = seller_data.password or secrets.token_urlsafe(12)
    
    # Create seller admin account
    new_seller = Admin(
        email=seller_data.email,
        name=seller_data.name,
        password_hash=get_password_hash(password),
        role=AdminRole.SELLER,
        company_id=seller_data.company_id,
        is_active=True
    )
    
    db.add(new_seller)
    db.commit()
    db.refresh(new_seller)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="seller_created",
        entity_type="admin",
        entity_id=new_seller.id,
        details={
            "seller_name": new_seller.name,
            "seller_email": new_seller.email,
            "company_id": seller_data.company_id,
            "company_name": company.name
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": str(new_seller.id),
            "email": new_seller.email,
            "name": new_seller.name,
            "role": new_seller.role.value,
            "company": {
                "id": company.id,
                "name": company.name
            },
            "temporary_password": password if not seller_data.password else None,
            "is_active": new_seller.is_active,
            "created_at": new_seller.created_at.isoformat() if new_seller.created_at else None
        },
        message="Seller created successfully. Share the temporary password with the seller."
    )


@router.get("", response_model=ResponseModel)
async def list_sellers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all sellers with filters.
    Only admins and super admins can view sellers list.
    """
    query = db.query(Admin).filter(Admin.role == AdminRole.SELLER)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Admin.name.ilike(f"%{search}%"),
                Admin.email.ilike(f"%{search}%")
            )
        )
    
    if company_id:
        query = query.filter(Admin.company_id == company_id)
    
    if is_active is not None:
        query = query.filter(Admin.is_active == is_active)
    
    # Order by created_at descending
    query = query.order_by(Admin.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    sellers = query.offset(offset).limit(limit).all()
    
    # Format response
    seller_list = []
    for seller in sellers:
        # Get company info
        company_data = None
        if seller.company:
            company_data = {
                "id": seller.company.id,
                "name": seller.company.name
            }
        
        # Count products created by this seller
        from app.models.product import Product
        product_count = db.query(Product).filter(Product.created_by == str(seller.id)).count()
        
        seller_data = {
            "id": str(seller.id),
            "email": seller.email,
            "name": seller.name,
            "role": seller.role.value,
            "company": company_data,
            "is_active": seller.is_active,
            "product_count": product_count,
            "last_login": seller.last_login.isoformat() if seller.last_login else None,
            "created_at": seller.created_at.isoformat() if seller.created_at else None
        }
        seller_list.append(seller_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": seller_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 0
            }
        },
        message="Sellers retrieved successfully"
    )


@router.get("/{seller_id}", response_model=ResponseModel)
async def get_seller(
    seller_id: str,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get seller details.
    Only admins and super admins can view seller details.
    """
    try:
        seller_uuid = UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller ID format")
    
    seller = db.query(Admin).filter(
        Admin.id == seller_uuid,
        Admin.role == AdminRole.SELLER
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Get company info
    company_data = None
    if seller.company:
        company_data = {
            "id": seller.company.id,
            "name": seller.company.name,
            "logo": seller.company.logo_url or seller.company.logo
        }
    
    # Get product statistics
    from app.models.product import Product
    total_products = db.query(Product).filter(Product.created_by == str(seller.id)).count()
    active_products = db.query(Product).filter(
        Product.created_by == str(seller.id),
        Product.is_available == True
    ).count()
    
    seller_data = {
        "id": str(seller.id),
        "email": seller.email,
        "name": seller.name,
        "role": seller.role.value,
        "company": company_data,
        "is_active": seller.is_active,
        "statistics": {
            "total_products": total_products,
            "active_products": active_products
        },
        "last_login": seller.last_login.isoformat() if seller.last_login else None,
        "created_at": seller.created_at.isoformat() if seller.created_at else None,
        "updated_at": seller.updated_at.isoformat() if seller.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=seller_data,
        message="Seller retrieved successfully"
    )


@router.put("/{seller_id}", response_model=ResponseModel)
async def update_seller(
    seller_id: str,
    seller_data: UpdateSellerRequest,
    request: Request,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update seller details.
    Only admins and super admins can update sellers.
    """
    try:
        seller_uuid = UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller ID format")
    
    seller = db.query(Admin).filter(
        Admin.id == seller_uuid,
        Admin.role == AdminRole.SELLER
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Update fields
    if seller_data.name is not None:
        seller.name = seller_data.name
    
    if seller_data.email is not None:
        # Check if email already exists
        existing_admin = db.query(Admin).filter(
            Admin.email == seller_data.email,
            Admin.id != seller_uuid
        ).first()
        if existing_admin:
            raise HTTPException(status_code=400, detail="Email already in use")
        seller.email = seller_data.email
    
    if seller_data.company_id is not None:
        # Verify company exists
        company = db.query(Company).filter(Company.id == seller_data.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        seller.company_id = seller_data.company_id
    
    if seller_data.is_active is not None:
        seller.is_active = seller_data.is_active
    
    db.commit()
    db.refresh(seller)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="seller_updated",
        entity_type="admin",
        entity_id=seller.id,
        details={
            "seller_name": seller.name,
            "seller_email": seller.email,
            "is_active": seller.is_active
        },
        request=request
    )
    
    # Get company info
    company_data = None
    if seller.company:
        company_data = {
            "id": seller.company.id,
            "name": seller.company.name
        }
    
    return ResponseModel(
        success=True,
        data={
            "id": str(seller.id),
            "email": seller.email,
            "name": seller.name,
            "role": seller.role.value,
            "company": company_data,
            "is_active": seller.is_active,
            "updated_at": seller.updated_at.isoformat() if seller.updated_at else None
        },
        message="Seller updated successfully"
    )


@router.delete("/{seller_id}", response_model=ResponseModel)
async def delete_seller(
    seller_id: str,
    request: Request,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete/deactivate a seller.
    Only admins and super admins can delete sellers.
    """
    try:
        seller_uuid = UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller ID format")
    
    seller = db.query(Admin).filter(
        Admin.id == seller_uuid,
        Admin.role == AdminRole.SELLER
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Instead of deleting, we deactivate the seller
    seller.is_active = False
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="seller_deleted",
        entity_type="admin",
        entity_id=seller.id,
        details={
            "seller_name": seller.name,
            "seller_email": seller.email
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Seller deactivated successfully"
    )


@router.post("/{seller_id}/reset-password", response_model=ResponseModel)
async def reset_seller_password(
    seller_id: str,
    request: Request,
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Reset seller password and generate a new temporary password.
    Only admins and super admins can reset seller passwords.
    """
    try:
        seller_uuid = UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller ID format")
    
    seller = db.query(Admin).filter(
        Admin.id == seller_uuid,
        Admin.role == AdminRole.SELLER
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Generate new temporary password
    new_password = secrets.token_urlsafe(12)
    seller.password_hash = get_password_hash(new_password)
    
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="seller_password_reset",
        entity_type="admin",
        entity_id=seller.id,
        details={
            "seller_name": seller.name,
            "seller_email": seller.email
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "temporary_password": new_password
        },
        message="Seller password reset successfully. Share the temporary password with the seller."
    )
