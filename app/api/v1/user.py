from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import UserResponse, UserUpdate, ChangePassword
from app.schemas.common import ResponseModel
from app.models.user import User
from app.utils.security import verify_password, get_password_hash

router = APIRouter()


@router.get("/profile", response_model=ResponseModel)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile with both snake_case and camelCase fields for frontend compatibility"""
    # Refresh user from database to get latest kyc_status
    db.refresh(current_user)
    # Get KYC status as string
    kyc_status = current_user.kyc_status.value if hasattr(current_user.kyc_status, 'value') else str(current_user.kyc_status)
    is_kyc_verified = kyc_status == "verified"
    
    # Extract business address details from address JSON if available
    business_address = None
    business_city = None
    business_state = None
    business_pincode = None
    if current_user.address and isinstance(current_user.address, dict):
        business_address = current_user.address.get("address") or current_user.address.get("business_address")
        business_city = current_user.address.get("city") or current_user.address.get("business_city")
        business_state = current_user.address.get("state") or current_user.address.get("business_state")
        business_pincode = current_user.address.get("pincode") or current_user.address.get("business_pincode")
    
    # Get KYC submission date from KYC records
    kyc_submitted_at = None
    if hasattr(current_user, 'kyc_records') and current_user.kyc_records:
        # Get the most recent KYC record
        latest_kyc = max(current_user.kyc_records, key=lambda k: k.created_at if k.created_at else datetime.min)
        kyc_submitted_at = latest_kyc.created_at.isoformat() if latest_kyc.created_at else None
    
    # Build response with both snake_case and camelCase fields
    profile_data = {
        "id": current_user.id,
        "name": current_user.name,
        "full_name": current_user.name,  # Alternative field name
        "email": current_user.email,
        "phone": current_user.phone,
        "phone_number": current_user.phone,  # Alternative field name
        "business_name": current_user.business_name,
        "businessName": current_user.business_name,  # camelCase alternative
        "business_type": None,  # Not in model yet, can be added to address JSON
        "businessType": None,  # camelCase alternative
        "gst_number": current_user.gst_number,
        "gstNumber": current_user.gst_number,  # camelCase alternative
        "pan_number": current_user.pan_number,
        "panNumber": current_user.pan_number,  # camelCase alternative
        "business_address": business_address,
        "businessAddress": business_address,  # camelCase alternative
        "business_city": business_city,
        "businessCity": business_city,  # camelCase alternative
        "business_state": business_state,
        "businessState": business_state,  # camelCase alternative
        "business_pincode": business_pincode,
        "businessPincode": business_pincode,  # camelCase alternative
        "avatar_url": None,  # Not implemented yet, can be added later
        "avatarUrl": None,  # camelCase alternative
        "kyc_status": kyc_status,
        "kycStatus": kyc_status,  # camelCase alternative
        "is_kyc_verified": is_kyc_verified,  # Boolean alternative
        "kyc_submitted_at": kyc_submitted_at,  # Optional: when KYC was submitted
        "kyc_verified_at": current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None,  # Optional: when KYC was verified
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=profile_data,
        message="Profile fetched successfully"
    )


@router.put("/profile", response_model=ResponseModel)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile with validation"""
    import re
    
    # Update name
    if user_data.name:
        if len(user_data.name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        current_user.name = user_data.name
    
    # Update phone (support both phone and phone_number)
    phone_to_update = user_data.phone or user_data.phone_number
    if phone_to_update:
        # Check if phone already exists
        existing_user = db.query(User).filter(
            User.phone == phone_to_update,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Phone number already in use")
        current_user.phone = phone_to_update
    
    # Update business name
    if user_data.business_name:
        if len(user_data.business_name) < 2:
            raise HTTPException(status_code=400, detail="Business name must be at least 2 characters")
        current_user.business_name = user_data.business_name
    
    # Update GST number with validation
    if user_data.gst_number is not None:
        if user_data.gst_number and len(user_data.gst_number) != 15:
            raise HTTPException(status_code=400, detail="GST number must be 15 characters")
        # Format validation: 2 digits (state) + 10 alphanumeric (PAN) + 1 char (1-9 or A-Z) + 1 char (Z) + 1 digit (checksum)
        # Correct format: ^\d{2}[A-Z0-9]{10}[1-9A-Z]Z\d$
        if user_data.gst_number and not re.match(r'^\d{2}[A-Z0-9]{10}[1-9A-Z]Z\d$', user_data.gst_number.upper()):
            raise HTTPException(status_code=400, detail="Invalid GST number format")
        current_user.gst_number = user_data.gst_number.upper() if user_data.gst_number else None
    
    # Update PAN number with validation
    if user_data.pan_number is not None:
        if user_data.pan_number and len(user_data.pan_number) != 10:
            raise HTTPException(status_code=400, detail="PAN number must be 10 characters")
        # Format validation: 5 letters + 4 digits + 1 letter
        if user_data.pan_number and not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', user_data.pan_number.upper()):
            raise HTTPException(status_code=400, detail="Invalid PAN number format")
        current_user.pan_number = user_data.pan_number.upper() if user_data.pan_number else None
    
    # Update business address details (store in address JSON)
    address_dict = current_user.address if current_user.address else {}
    if user_data.business_address is not None:
        address_dict["business_address"] = user_data.business_address
        address_dict["address"] = user_data.business_address  # Also set legacy field
    if user_data.business_city is not None:
        address_dict["business_city"] = user_data.business_city
        address_dict["city"] = user_data.business_city  # Also set legacy field
    if user_data.business_state is not None:
        address_dict["business_state"] = user_data.business_state
        address_dict["state"] = user_data.business_state  # Also set legacy field
    if user_data.business_pincode is not None:
        if user_data.business_pincode and (len(user_data.business_pincode) != 6 or not user_data.business_pincode.isdigit()):
            raise HTTPException(status_code=400, detail="Pincode must be exactly 6 digits")
        address_dict["business_pincode"] = user_data.business_pincode
        address_dict["pincode"] = user_data.business_pincode  # Also set legacy field
    if user_data.business_type is not None:
        if user_data.business_type not in ["Retail", "Wholesale", "Distributor"]:
            raise HTTPException(status_code=400, detail="Business type must be Retail, Wholesale, or Distributor")
        address_dict["business_type"] = user_data.business_type
    
    if address_dict:
        current_user.address = address_dict
    
    # Support legacy address field
    if user_data.address:
        current_user.address = user_data.address
    
    db.commit()
    db.refresh(current_user)
    
    # Return updated profile with all fields
    kyc_status = current_user.kyc_status.value if hasattr(current_user.kyc_status, 'value') else str(current_user.kyc_status)
    is_kyc_verified = kyc_status == "verified"
    
    business_address = None
    business_city = None
    business_state = None
    business_pincode = None
    business_type = None
    if current_user.address and isinstance(current_user.address, dict):
        business_address = current_user.address.get("business_address") or current_user.address.get("address")
        business_city = current_user.address.get("business_city") or current_user.address.get("city")
        business_state = current_user.address.get("business_state") or current_user.address.get("state")
        business_pincode = current_user.address.get("business_pincode") or current_user.address.get("pincode")
        business_type = current_user.address.get("business_type")
    
    profile_data = {
        "id": current_user.id,
        "name": current_user.name,
        "full_name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "phone_number": current_user.phone,
        "business_name": current_user.business_name,
        "businessName": current_user.business_name,
        "business_type": business_type,
        "businessType": business_type,
        "gst_number": current_user.gst_number,
        "gstNumber": current_user.gst_number,
        "pan_number": current_user.pan_number,
        "panNumber": current_user.pan_number,
        "business_address": business_address,
        "businessAddress": business_address,
        "business_city": business_city,
        "businessCity": business_city,
        "business_state": business_state,
        "businessState": business_state,
        "business_pincode": business_pincode,
        "businessPincode": business_pincode,
        "avatar_url": None,
        "avatarUrl": None,
        "kyc_status": kyc_status,
        "kycStatus": kyc_status,
        "is_kyc_verified": is_kyc_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=profile_data,
        message="Profile updated successfully"
    )


@router.post("/change-password", response_model=ResponseModel)
def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return ResponseModel(success=True, message="Password changed successfully")

