from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.delivery import DeliveryLocationCreate, DeliveryLocationResponse, DeliveryCheck, DeliveryAvailabilityResponse
from app.schemas.common import ResponseModel
from app.models.delivery_location import DeliveryLocation
from decimal import Decimal
from uuid import UUID

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_delivery_locations(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's delivery locations"""
    locations = db.query(DeliveryLocation).filter(
        DeliveryLocation.user_id == str(current_user.id)
    ).order_by(DeliveryLocation.is_default.desc(), DeliveryLocation.created_at.desc()).all()
    
    return ResponseModel(
        success=True,
        data=[DeliveryLocationResponse.model_validate(l) for l in locations]
    )


@router.post("", response_model=ResponseModel, status_code=201)
def add_delivery_location(
    location_data: DeliveryLocationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add delivery location"""
    # If this is set as default, unset other defaults
    if location_data.is_default:
        db.query(DeliveryLocation).filter(
            DeliveryLocation.user_id == str(current_user.id)
        ).update({"is_default": False})
    
    location = DeliveryLocation(
        user_id=str(current_user.id),
        address=location_data.address,
        city=location_data.city,
        state=location_data.state,
        pincode=location_data.pincode,
        landmark=location_data.landmark,
        type=location_data.type,
        is_default=location_data.is_default
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    
    return ResponseModel(
        success=True,
        data=DeliveryLocationResponse.model_validate(location),
        message="Delivery location added"
    )


@router.post("/check-availability", response_model=ResponseModel)
def check_delivery_availability(
    check_data: DeliveryCheck,
    db: Session = Depends(get_db)
):
    """Check delivery availability for pincode"""
    # Simple logic - in production, use actual delivery service API
    pincode = check_data.pincode
    
    # Example: Some pincodes are not serviceable
    non_serviceable = ["000000", "999999"]
    
    is_available = pincode not in non_serviceable and len(pincode) == 6
    
    # Estimate delivery days (2-5 days)
    estimated_days = 3 if is_available else 0
    
    # Delivery charge (free above 1000, else 50)
    delivery_charge = Decimal('0.00') if is_available else Decimal('50.00')
    
    return ResponseModel(
        success=True,
        data=DeliveryAvailabilityResponse(
            is_available=is_available,
            estimated_days=estimated_days,
            delivery_charge=delivery_charge
        )
    )


@router.put("/{location_id}", response_model=ResponseModel)
def update_delivery_location(
    location_id: UUID,
    location_data: DeliveryLocationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update delivery location"""
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.id == str(location_id),
        DeliveryLocation.user_id == str(current_user.id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Delivery location not found")
    
    # If this is set as default, unset other defaults
    if location_data.is_default:
        db.query(DeliveryLocation).filter(
            DeliveryLocation.user_id == str(current_user.id),
            DeliveryLocation.id != str(location_id)
        ).update({"is_default": False})
    
    location.address = location_data.address
    location.city = location_data.city
    location.state = location_data.state
    location.pincode = location_data.pincode
    location.landmark = location_data.landmark
    location.type = location_data.type
    location.is_default = location_data.is_default
    
    db.commit()
    db.refresh(location)
    
    return ResponseModel(
        success=True,
        data=DeliveryLocationResponse.model_validate(location),
        message="Delivery location updated"
    )


@router.delete("/{location_id}", response_model=ResponseModel)
def delete_delivery_location(
    location_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete delivery location"""
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.id == str(location_id),
        DeliveryLocation.user_id == str(current_user.id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Delivery location not found")
    
    db.delete(location)
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Delivery location deleted"
    )

