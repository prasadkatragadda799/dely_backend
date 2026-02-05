"""
Admin Offers Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
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
from app.api.v1.admin_upload import save_uploaded_file
from app.utils.admin_activity import log_admin_activity
from app.models.admin import Admin

router = APIRouter()

def _parse_date(value: Optional[str], field_name: str) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}. Expected YYYY-MM-DD")


@router.get("", response_model=ResponseModel)
async def list_offers(
    type: Optional[str] = Query(None, pattern="^(banner|text|company)$"),
    status: Optional[str] = Query(None, pattern="^(active|inactive)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all offers with filters (type, status). Hub sends ?type= & ?status= """
    query = db.query(Offer)
    
    # Apply filters
    if type:
        try:
            offer_type = OfferType(type)
            query = query.filter(Offer.type == offer_type)
        except ValueError:
            pass
    
    if status == "active":
        query = query.filter(Offer.is_active == True)
    elif status == "inactive":
        query = query.filter(Offer.is_active == False)
    
    # Order by created_at desc
    offers = query.order_by(Offer.created_at.desc()).all()
    
    offer_list = []
    for offer in offers:
        offer_data = {
            "id": offer.id,
            "title": offer.title,
            "type": offer.type.value,
            "offer_type": offer.type.value,
            "description": offer.description,
            "image": offer.image,
            "imageUrl": offer.image,
            "image_url": offer.image,
            "validFrom": offer.valid_from,
            "valid_from": offer.valid_from.isoformat() if offer.valid_from else None,
            "validTo": offer.valid_to,
            "valid_to": offer.valid_to.isoformat() if offer.valid_to else None,
            "status": "active" if offer.is_active else "inactive",
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
    offer_id: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get offer details"""
    offer = db.query(Offer).filter(Offer.id == str(offer_id)).first()
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
    request: Request,
    # Admin Hub sends FormData (multipart/form-data)
    title: str = Form(...),
    type: str = Form(...),
    description: Optional[str] = Form(None),
    validFrom: str = Form(...),
    validTo: str = Form(...),
    image: Optional[UploadFile] = File(None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new offer"""
    try:
        offer_type = OfferType(type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid type. Use banner|text|company")

    valid_from = _parse_date(validFrom, "validFrom")
    valid_to = _parse_date(validTo, "validTo")
    if not valid_from or not valid_to:
        raise HTTPException(status_code=400, detail="validFrom and validTo are required")
    if valid_from > valid_to:
        raise HTTPException(status_code=400, detail="validFrom cannot be after validTo")

    image_url = None
    if image is not None:
        # Store offer image under /uploads/offer/...
        image_url = save_uploaded_file(image, "offer", None, request)
    
    offer = Offer(
        title=title,
        type=offer_type,
        description=description,
        image=image_url,
        # Note: company_id column doesn't exist in database table yet
        # company_id=offer_data.company_id,
        valid_from=valid_from,
        valid_to=valid_to,
        is_active=True
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


@router.put("/{offer_id}/toggle", response_model=ResponseModel)
async def toggle_offer(
    offer_id: str,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Toggle offer active/inactive status."""
    offer = db.query(Offer).filter(Offer.id == str(offer_id)).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.is_active = not offer.is_active
    db.commit()
    db.refresh(offer)
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="offer_toggled",
        entity_type="offer",
        entity_id=offer_id,
        details={"is_active": offer.is_active},
        request=request
    )
    return ResponseModel(
        success=True,
        data={"id": offer.id, "isActive": offer.is_active, "status": "active" if offer.is_active else "inactive"},
        message="Offer status updated"
    )


@router.put("/{offer_id}", response_model=ResponseModel)
async def update_offer(
    offer_id: str,
    request: Request,
    # Admin Hub sends FormData (multipart/form-data). All fields optional for partial update.
    title: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    validFrom: Optional[str] = Form(None),
    validTo: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update an offer"""
    offer = db.query(Offer).filter(Offer.id == str(offer_id)).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    update_details: dict = {}

    if type is not None:
        try:
            offer.type = OfferType(type)
            update_details["type"] = type
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid type. Use banner|text|company")
    if title is not None:
        offer.title = title
        update_details["title"] = title
    if description is not None:
        offer.description = description
        update_details["description"] = description

    # Dates (partial update)
    new_valid_from = _parse_date(validFrom, "validFrom") if validFrom is not None else offer.valid_from
    new_valid_to = _parse_date(validTo, "validTo") if validTo is not None else offer.valid_to
    if new_valid_from and new_valid_to and new_valid_from > new_valid_to:
        raise HTTPException(status_code=400, detail="validFrom cannot be after validTo")
    offer.valid_from = new_valid_from
    offer.valid_to = new_valid_to
    if validFrom is not None:
        update_details["validFrom"] = validFrom
    if validTo is not None:
        update_details["validTo"] = validTo

    if image is not None:
        offer.image = save_uploaded_file(image, "offer", None, request)
        update_details["image"] = True
    
    db.commit()
    db.refresh(offer)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="offer_updated",
        entity_type="offer",
        entity_id=offer_id,
        details=update_details,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminOfferResponse.model_validate(offer),
        message="Offer updated successfully"
    )


@router.delete("/{offer_id}", response_model=ResponseModel)
async def delete_offer(
    offer_id: str,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete an offer"""
    offer = db.query(Offer).filter(Offer.id == str(offer_id)).first()
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

