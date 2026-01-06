"""
Admin Offers Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from app.database import get_db
from app.schemas.admin_offer import (
    AdminOfferCreate, AdminOfferUpdate, AdminOfferResponse
)
from app.schemas.common import ResponseModel
from app.models.offer import Offer, OfferType
from app.models.company import Company
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.models.admin import Admin

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_offers(
    type: Optional[str] = Query(None, pattern="^(banner|text|company)$"),
    status_filter: Optional[str] = Query(None, pattern="^(active|inactive)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all offers with filters"""
    query = db.query(Offer)
    
    # Apply filters
    if type:
        try:
            offer_type = OfferType(type)
            query = query.filter(Offer.type == offer_type)
        except ValueError:
            pass
    
    if status_filter == "active":
        query = query.filter(Offer.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(Offer.is_active == False)
    
    # Order by created_at desc
    offers = query.order_by(Offer.created_at.desc()).all()
    
    offer_list = []
    for offer in offers:
        offer_data = {
            "id": offer.id,
            "title": offer.title,
            "type": offer.type.value,
            "description": offer.description,
            "imageUrl": offer.image,  # Use image field (image_url column doesn't exist in DB)
            "validFrom": offer.valid_from,
            "validTo": offer.valid_to,
            "isActive": offer.is_active,
            "createdAt": offer.created_at,
            "updatedAt": offer.updated_at
        }
        
        if offer.company:
            offer_data["company"] = {
                "id": offer.company.id,
                "name": offer.company.name,
                "logoUrl": offer.company.logo_url or offer.company.logo
            }
        
        offer_list.append(offer_data)
    
    return ResponseModel(
        success=True,
        data=offer_list,
        message="Offers retrieved successfully"
    )


@router.get("/{offer_id}", response_model=ResponseModel)
async def get_offer(
    offer_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get offer details"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer_data = AdminOfferResponse.model_validate(offer)
    if offer.company:
        offer_data.company = {
            "id": offer.company.id,
            "name": offer.company.name,
            "logoUrl": offer.company.logo_url or offer.company.logo
        }
    
    return ResponseModel(
        success=True,
        data=offer_data,
        message="Offer retrieved successfully"
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_offer(
    offer_data: AdminOfferCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new offer"""
    # Validate date range
    if offer_data.valid_from > offer_data.valid_to:
        raise HTTPException(
            status_code=400,
            detail="valid_from cannot be after valid_to"
        )
    
    # Validate company_id if provided
    if offer_data.company_id:
        company = db.query(Company).filter(Company.id == offer_data.company_id).first()
        if not company:
            raise HTTPException(
                status_code=400,
                detail="Company not found"
            )
    
    offer = Offer(
        title=offer_data.title,
        type=offer_data.type,
        description=offer_data.description,
        image=offer_data.image_url,  # Map image_url from schema to image field in model
        # Note: company_id column doesn't exist in database table yet
        # company_id=offer_data.company_id,
        valid_from=offer_data.valid_from,
        valid_to=offer_data.valid_to,
        is_active=offer_data.is_active
    )
    
    db.add(offer)
    db.commit()
    db.refresh(offer)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="offer_created",
        entity_type="offer",
        entity_id=offer.id,
        details={"title": offer.title, "type": offer.type.value},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminOfferResponse.model_validate(offer),
        message="Offer created successfully"
    )


@router.put("/{offer_id}", response_model=ResponseModel)
async def update_offer(
    offer_id: UUID,
    offer_data: AdminOfferUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update an offer"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Validate date range if dates are being updated
    valid_from = offer_data.valid_from if offer_data.valid_from else offer.valid_from
    valid_to = offer_data.valid_to if offer_data.valid_to else offer.valid_to
    
    if valid_from > valid_to:
        raise HTTPException(
            status_code=400,
            detail="valid_from cannot be after valid_to"
        )
    
    # Validate company_id if provided
    if offer_data.company_id:
        company = db.query(Company).filter(Company.id == offer_data.company_id).first()
        if not company:
            raise HTTPException(
                status_code=400,
                detail="Company not found"
            )
    
    # Update fields
    update_data = offer_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "image_url":
            # Map image_url from schema to image field in model
            setattr(offer, "image", value)
        elif key == "company_id":
            # Skip company_id - column doesn't exist in database table yet
            pass
        elif hasattr(offer, key):
            setattr(offer, key, value)
    
    db.commit()
    db.refresh(offer)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="offer_updated",
        entity_type="offer",
        entity_id=offer_id,
        details=update_data,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminOfferResponse.model_validate(offer),
        message="Offer updated successfully"
    )


@router.delete("/{offer_id}", response_model=ResponseModel)
async def delete_offer(
    offer_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete an offer"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer_title = offer.title
    db.delete(offer)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="offer_deleted",
        entity_type="offer",
        entity_id=offer_id,
        details={"title": offer_title},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Offer deleted successfully"
    )

