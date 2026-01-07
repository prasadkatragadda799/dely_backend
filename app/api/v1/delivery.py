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
    
    # Format locations with proper field mapping
    location_list = []
    for loc in locations:
        location_dict = {
            "id": loc.id,
            "user_id": loc.user_id,
            "address_line1": loc.address,  # Map address to address_line1
            "address_line2": loc.landmark,  # Map landmark to address_line2
            "address": loc.address,  # Legacy support
            "city": loc.city,
            "state": loc.state,
            "pincode": loc.pincode,
            "landmark": loc.landmark,  # Legacy support
            "type": loc.type,
            "is_default": loc.is_default,
            "created_at": loc.created_at.isoformat() if loc.created_at else None,
            "updated_at": loc.updated_at.isoformat() if hasattr(loc, 'updated_at') and loc.updated_at else None
        }
        location_list.append(location_dict)
    
    return ResponseModel(
        success=True,
        data=location_list,
        message="Addresses fetched successfully"
    )


@router.post("", response_model=ResponseModel, status_code=201)
def add_delivery_location(
    location_data: DeliveryLocationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add delivery location with validation"""
    import re
    
    # Validate required fields
    address_line1 = location_data.address_line1 or location_data.address
    if not address_line1 or len(address_line1) < 5:
        raise HTTPException(status_code=400, detail="Address line 1 must be at least 5 characters")
    
    if not location_data.city or len(location_data.city) < 2:
        raise HTTPException(status_code=400, detail="City must be at least 2 characters")
    
    if not location_data.state or len(location_data.state) < 2:
        raise HTTPException(status_code=400, detail="State must be at least 2 characters")
    
    if not location_data.pincode or len(location_data.pincode) != 6 or not location_data.pincode.isdigit():
        raise HTTPException(status_code=400, detail="Pincode must be exactly 6 digits")
    
    if location_data.type not in ["home", "office", "other"]:
        raise HTTPException(status_code=400, detail="Type must be 'home', 'office', or 'other'")
    
    # If this is set as default, unset other defaults
    if location_data.is_default:
        db.query(DeliveryLocation).filter(
            DeliveryLocation.user_id == str(current_user.id)
        ).update({"is_default": False})
    
    location = DeliveryLocation(
        user_id=str(current_user.id),
        address=address_line1,  # Store in address field (maps to address_line1)
        city=location_data.city,
        state=location_data.state,
        pincode=location_data.pincode,
        landmark=location_data.address_line2 or location_data.landmark,  # Store in landmark field (maps to address_line2)
        type=location_data.type,
        is_default=location_data.is_default
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    
    # Format response with proper field mapping
    location_dict = {
        "id": location.id,
        "user_id": location.user_id,
        "address_line1": location.address,
        "address_line2": location.landmark,
        "address": location.address,  # Legacy support
        "city": location.city,
        "state": location.state,
        "pincode": location.pincode,
        "landmark": location.landmark,  # Legacy support
        "type": location.type,
        "is_default": location.is_default,
        "created_at": location.created_at.isoformat() if location.created_at else None,
        "updated_at": location.updated_at.isoformat() if hasattr(location, 'updated_at') and location.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=location_dict,
        message="Address added successfully"
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
    """Update delivery location with validation"""
    import re
    
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.id == str(location_id),
        DeliveryLocation.user_id == str(current_user.id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Delivery location not found")
    
    # Validate fields if provided
    address_line1 = location_data.address_line1 or location_data.address
    if address_line1 and len(address_line1) < 5:
        raise HTTPException(status_code=400, detail="Address line 1 must be at least 5 characters")
    
    if location_data.city and len(location_data.city) < 2:
        raise HTTPException(status_code=400, detail="City must be at least 2 characters")
    
    if location_data.state and len(location_data.state) < 2:
        raise HTTPException(status_code=400, detail="State must be at least 2 characters")
    
    if location_data.pincode and (len(location_data.pincode) != 6 or not location_data.pincode.isdigit()):
        raise HTTPException(status_code=400, detail="Pincode must be exactly 6 digits")
    
    if location_data.type and location_data.type not in ["home", "office", "other"]:
        raise HTTPException(status_code=400, detail="Type must be 'home', 'office', or 'other'")
    
    # If this is set as default, unset other defaults
    if location_data.is_default:
        db.query(DeliveryLocation).filter(
            DeliveryLocation.user_id == str(current_user.id),
            DeliveryLocation.id != str(location_id)
        ).update({"is_default": False})
    
    # Update fields
    if address_line1:
        location.address = address_line1
    if location_data.city:
        location.city = location_data.city
    if location_data.state:
        location.state = location_data.state
    if location_data.pincode:
        location.pincode = location_data.pincode
    if location_data.address_line2 is not None or location_data.landmark is not None:
        location.landmark = location_data.address_line2 or location_data.landmark
    if location_data.type:
        location.type = location_data.type
    location.is_default = location_data.is_default
    
    db.commit()
    db.refresh(location)
    
    # Format response with proper field mapping
    location_dict = {
        "id": location.id,
        "user_id": location.user_id,
        "address_line1": location.address,
        "address_line2": location.landmark,
        "address": location.address,  # Legacy support
        "city": location.city,
        "state": location.state,
        "pincode": location.pincode,
        "landmark": location.landmark,  # Legacy support
        "type": location.type,
        "is_default": location.is_default,
        "created_at": location.created_at.isoformat() if location.created_at else None,
        "updated_at": location.updated_at.isoformat() if hasattr(location, 'updated_at') and location.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=location_dict,
        message="Address updated successfully"
    )


@router.delete("/{location_id}", response_model=ResponseModel)
def delete_delivery_location(
    location_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete delivery location with validation"""
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.id == str(location_id),
        DeliveryLocation.user_id == str(current_user.id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Delivery location not found")
    
    # Check if this is the only address
    address_count = db.query(DeliveryLocation).filter(
        DeliveryLocation.user_id == str(current_user.id)
    ).count()
    
    if address_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only address")
    
    was_default = location.is_default
    
    db.delete(location)
    db.commit()
    
    # If deleted address was default, set another address as default
    if was_default:
        remaining_location = db.query(DeliveryLocation).filter(
            DeliveryLocation.user_id == str(current_user.id)
        ).first()
        if remaining_location:
            remaining_location.is_default = True
            db.commit()
    
    return ResponseModel(
        success=True,
        message="Address deleted successfully"
    )

