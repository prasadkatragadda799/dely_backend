from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import UserResponse, UserUpdate, ChangePassword
from app.schemas.common import ResponseModel
from app.schemas.admin_report import UserActivityCreate
from app.models.user import User
from app.models.user_activity_log import UserActivityLog
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
    # Get KYC status as string, normalize to lowercase
    kyc_status_raw = current_user.kyc_status.value if hasattr(current_user.kyc_status, 'value') else str(current_user.kyc_status)
    kyc_status = kyc_status_raw.lower()  # Normalize to lowercase
    is_kyc_verified = kyc_status == "verified"
    
    # Extract business address details from address JSON if available
    business_address = None
    business_city = None
    business_state = None
    business_pincode = None
    latitude = None
    longitude = None
    if current_user.address and isinstance(current_user.address, dict):
        business_address = current_user.address.get("address") or current_user.address.get("business_address")
        business_city = current_user.address.get("city") or current_user.address.get("business_city")
        business_state = current_user.address.get("state") or current_user.address.get("business_state")
        business_pincode = current_user.address.get("pincode") or current_user.address.get("business_pincode")
        latitude = current_user.address.get("latitude")
        longitude = current_user.address.get("longitude")

    # Derive plain profile location fields expected by mobile app
    city_value = current_user.city or business_city
    state_value = current_user.state or business_state
    pincode_value = current_user.pincode or business_pincode
    address_value = business_address
    
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
        "fssai_number": current_user.fssai_number,
        "fssaiNumber": current_user.fssai_number,  # camelCase alternative
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
        # Plain location fields for EditProfileScreen
        "city": city_value,
        "state": state_value,
        "pincode": pincode_value,
        "pin_code": pincode_value,
        "address": address_value,
        "latitude": latitude,
        "longitude": longitude,
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
    
    # Update FSSAI license number with validation (digits only, exactly 14)
    fssai_to_update = user_data.fssaiNumber or user_data.fssai_number
    if fssai_to_update is not None:
        fssai_clean = str(fssai_to_update).strip()
        if fssai_clean and not re.fullmatch(r"^\d{14}$", fssai_clean):
            raise HTTPException(status_code=400, detail="Invalid FSSAI license number. It must be exactly 14 digits.")
        current_user.fssai_number = fssai_clean if fssai_clean else None

    # Legacy: Update PAN number if provided (kept for old users)
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

    # Optional GPS coordinates from mobile app's "Get from GPS"
    if user_data.latitude is not None:
        address_dict["latitude"] = user_data.latitude
    if user_data.longitude is not None:
        address_dict["longitude"] = user_data.longitude
    
    if address_dict:
        current_user.address = address_dict
    
    # Support legacy address field
    if user_data.address:
        current_user.address = user_data.address
    
    # Update user location fields (for activity tracking)
    if user_data.city is not None:
        current_user.city = user_data.city
    if user_data.state is not None:
        current_user.state = user_data.state
    if user_data.pincode is not None:
        if user_data.pincode and (len(user_data.pincode) != 6 or not user_data.pincode.isdigit()):
            raise HTTPException(status_code=400, detail="Pincode must be exactly 6 digits")
        current_user.pincode = user_data.pincode
    
    db.commit()
    db.refresh(current_user)

    # If the user does not yet have any delivery locations, try to
    # auto-create a default one from their updated profile address.
    #
    # This keeps the behaviour intuitive for the mobile app:
    # - User fills/edit profile address (city/state/pincode/address)
    # - Checkout screens that rely on `/api/v1/delivery` see at least
    #   one usable delivery location instead of forcing the user to
    #   add the same address again.
    try:
        from app.models.delivery_location import DeliveryLocation

        has_location = (
            db.query(DeliveryLocation)
            .filter(DeliveryLocation.user_id == str(current_user.id))
            .count()
            > 0
        )

        if not has_location:
            # Prefer business_* fields stored in address JSON, but fall
            # back to the top-level city/state/pincode if needed.
            derived_address = None
            derived_city = None
            derived_state = None
            derived_pincode = None

            if current_user.address and isinstance(current_user.address, dict):
                derived_address = current_user.address.get("business_address") or current_user.address.get("address")
                derived_city = current_user.address.get("business_city") or current_user.address.get("city")
                derived_state = current_user.address.get("business_state") or current_user.address.get("state")
                derived_pincode = current_user.address.get("business_pincode") or current_user.address.get("pincode")

            # Fallbacks from user-level location fields
            derived_city = derived_city or current_user.city
            derived_state = derived_state or current_user.state
            derived_pincode = derived_pincode or current_user.pincode

            # Basic validation mirroring add_delivery_location rules
            if (
                derived_address
                and isinstance(derived_address, str)
                and len(derived_address.strip()) >= 5
                and derived_city
                and len(str(derived_city).strip()) >= 2
                and derived_state
                and len(str(derived_state).strip()) >= 2
                and derived_pincode
            ):
                pincode_str = str(derived_pincode).strip()
                if len(pincode_str) == 6 and pincode_str.isdigit():
                    location = DeliveryLocation(
                        user_id=str(current_user.id),
                        address=derived_address.strip(),
                        city=str(derived_city).strip(),
                        state=str(derived_state).strip(),
                        pincode=pincode_str,
                        landmark=None,
                        type="home",
                        is_default=True,
                    )
                    db.add(location)
                    db.commit()
    except Exception:
        # Never block profile updates because of address sync issues.
        pass

    # Return updated profile with all fields
    kyc_status = current_user.kyc_status.value if hasattr(current_user.kyc_status, 'value') else str(current_user.kyc_status)
    is_kyc_verified = kyc_status == "verified"
    
    business_address = None
    business_city = None
    business_state = None
    business_pincode = None
    business_type = None
    latitude = None
    longitude = None
    if current_user.address and isinstance(current_user.address, dict):
        business_address = current_user.address.get("business_address") or current_user.address.get("address")
        business_city = current_user.address.get("business_city") or current_user.address.get("city")
        business_state = current_user.address.get("business_state") or current_user.address.get("state")
        business_pincode = current_user.address.get("business_pincode") or current_user.address.get("pincode")
        business_type = current_user.address.get("business_type")
        latitude = current_user.address.get("latitude")
        longitude = current_user.address.get("longitude")

    city_value = current_user.city or business_city
    state_value = current_user.state or business_state
    pincode_value = current_user.pincode or business_pincode
    address_value = business_address
    
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
        "fssai_number": current_user.fssai_number,
        "fssaiNumber": current_user.fssai_number,
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
        # Plain location fields for EditProfileScreen
        "city": city_value,
        "state": state_value,
        "pincode": pincode_value,
        "pin_code": pincode_value,
        "address": address_value,
        "latitude": latitude,
        "longitude": longitude,
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


@router.post("/activity", response_model=ResponseModel)
def log_user_activity(
    activity_data: UserActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log user activity and update last_active_at timestamp.
    
    Activity types: 'login', 'order', 'view_product', 'app_open', etc.
    """
    # Update user's last_active_at timestamp
    current_user.last_active_at = datetime.utcnow()
    
    # Create activity log
    activity_log = UserActivityLog(
        user_id=current_user.id,
        activity_type=activity_data.activity_type,
        location_city=current_user.city,
        location_state=current_user.state,
        created_at=datetime.utcnow()
    )
    
    db.add(activity_log)
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Activity logged successfully"
    )

