from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import String, cast
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.kyc import GSTVerify, GSTVerifyResponse, KYCSubmit, KYCResponse, KYCStatusResponse
from app.schemas.common import ResponseModel
from app.models.kyc import KYC, KYCStatus
from app.models.user import User
from app.utils.gst_verification import verify_gst_number
from app.api.v1.admin_upload import save_uploaded_file

router = APIRouter()


@router.post("/verify-gst", response_model=ResponseModel)
def verify_gst(gst_data: GSTVerify, db: Session = Depends(get_db)):
    """Verify GST number - Returns mock data for now (no authentication required)"""
    import re
    
    try:
        # Get and clean GST number
        gst_number = (gst_data.gst_number or "").strip().upper()
        
        # Basic validation
        if not gst_number:
            raise HTTPException(
                status_code=400, 
                detail="GST number is required"
            )
        
        if len(gst_number) != 15:
            raise HTTPException(
                status_code=400, 
                detail="GST number must be exactly 15 characters"
            )
        
        # Verify GST number format: 2 digits (state) + 10 alphanumeric (PAN) + 1 char (1-9 or A-Z) + 1 char (Z) + 1 digit (checksum)
        # Correct format: ^\d{2}[A-Z0-9]{10}[1-9A-Z]Z\d$
        if not re.match(r'^\d{2}[A-Z0-9]{10}[1-9A-Z]Z[A-Z0-9]$', gst_number):
            raise HTTPException(
                status_code=400,
                detail="Invalid GST number format. Expected format: 2 digits (state) + 10 alphanumeric (PAN) + 1 char (1-9 or A-Z) + Z + 1 alphanumeric (checksum)"
            )
        
        # Get GST details (currently returns mock data)
        gst_details = verify_gst_number(gst_number)
        
        if not gst_details:
            raise HTTPException(
                status_code=400, 
                detail="Unable to verify GST number"
            )
        
        return ResponseModel(
            success=True,
            data=GSTVerifyResponse(**gst_details),
            message="GST number verified successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"GST Verification Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying GST number: {str(e)}"
        )


@router.post("/upload-image", response_model=ResponseModel)
async def upload_kyc_image(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload KYC image and return a server-accessible URL."""
    try:
        image_url = save_uploaded_file(
            file=file,
            upload_type="kyc",
            entity_id=current_user.id,
            request=request,
        )
        return ResponseModel(
            success=True,
            data={"url": image_url},
            message="KYC image uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading KYC image: {str(e)}")


@router.post("/submit", response_model=ResponseModel, status_code=201)
def submit_kyc(
    kyc_data: KYCSubmit,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit business KYC"""
    import re

    # Validate required fields
    if not kyc_data.business_name:
        raise HTTPException(status_code=400, detail="Business name is required")

    # Validate FSSAI only when provided
    if kyc_data.fssai_number and kyc_data.fssai_number.strip():
        fssai_clean = str(kyc_data.fssai_number).strip()
        if not re.fullmatch(r"^\d{14}$", fssai_clean):
            raise HTTPException(status_code=400, detail="Invalid FSSAI license number. It must be exactly 14 digits.")
        kyc_data.fssai_number = fssai_clean
    else:
        kyc_data.fssai_number = None
    
    # Check if KYC already exists (KYC.user_id and current_user.id are String(36))
    existing_kyc = db.query(KYC).filter(KYC.user_id == str(current_user.id)).first()
    
    # If KYC is already verified, return success response (recommended for better UX)
    if existing_kyc and existing_kyc.status == KYCStatus.VERIFIED:
        return ResponseModel(
            success=True,
            data={
                "kyc_id": str(existing_kyc.id) if existing_kyc.id else None,
                "status": existing_kyc.status.value,  # "verified" (lowercase)
                "verified_at": existing_kyc.verified_at.isoformat() if existing_kyc.verified_at else None
            },
            message="KYC is already verified"
        )
    
    # Verify GST only when provided
    if kyc_data.gst_number and kyc_data.gst_number.strip():
        gst_details = verify_gst_number(kyc_data.gst_number)
        if not gst_details:
            raise HTTPException(status_code=400, detail="Invalid GST number")

    # Normalize optional image URLs.
    # KYCSubmit.model_post_init currently defaults these to "" which would
    # bypass `if kyc.shop_image_url` checks in admin, so we convert "" -> None.
    shop_image_url = (kyc_data.shop_image_url or "").strip()
    fssai_license_image_url = (kyc_data.fssai_license_image_url or "").strip()
    shop_image_url = shop_image_url if shop_image_url else None
    fssai_license_image_url = fssai_license_image_url if fssai_license_image_url else None
    
    if existing_kyc:
        # Update existing KYC
        existing_kyc.business_name = kyc_data.business_name
        existing_kyc.gst_number = kyc_data.gst_number
        existing_kyc.fssai_number = kyc_data.fssai_number
        # Backward compatibility: store legacy PAN if provided, but never require it
        if kyc_data.pan_number:
            existing_kyc.pan_number = kyc_data.pan_number
        existing_kyc.business_type = kyc_data.business_type
        existing_kyc.address = kyc_data.address
        existing_kyc.shop_image_url = shop_image_url
        existing_kyc.fssai_license_image_url = fssai_license_image_url
        existing_kyc.documents = kyc_data.documents
        existing_kyc.status = KYCStatus.PENDING
        db.commit()
        # Don't refresh - object is already updated
        kyc = existing_kyc
    else:
        # Create new KYC (User.id and KYC.user_id are String(36))
        kyc = KYC(
            user_id=str(current_user.id),
            business_name=kyc_data.business_name,
            gst_number=kyc_data.gst_number,
            fssai_number=kyc_data.fssai_number,
            pan_number=kyc_data.pan_number or None,  # legacy (optional)
            business_type=kyc_data.business_type,
            address=kyc_data.address,
            shop_image_url=shop_image_url,
            fssai_license_image_url=fssai_license_image_url,
            documents=kyc_data.documents,
            status=KYCStatus.PENDING
        )
        db.add(kyc)
        db.commit()
        # Don't refresh - object is already populated with ID from commit
    
    # Update user KYC status and sync any newly submitted document URLs back to user columns
    # so the admin detail view (which reads user.xxx columns) always shows the latest docs.
    from app.models.user import KYCStatus as UserKYCStatus
    user_updates: dict = {"kyc_status": UserKYCStatus.PENDING.value}
    if kyc_data.documents and isinstance(kyc_data.documents, dict):
        for col, key in [
            ("gst_certificate", "gst_certificate"),
            ("udyam_registration", "udyam_registration"),
            ("trade_certificate", "trade_certificate"),
        ]:
            val = (kyc_data.documents.get(key) or "").strip()
            if val:
                user_updates[col] = val
    db.query(User).filter(User.id == current_user.id).update(user_updates)
    db.commit()
    # Refresh current_user object to get updated values
    db.refresh(current_user)
    
    # Convert UUID to string safely
    kyc_id_str = str(kyc.id) if kyc.id else None
    
    # Convert UUID to string safely - kyc.id is already available after commit
    kyc_id_str = str(kyc.id) if kyc.id else None
    
    return ResponseModel(
        success=True,
        data={
            "kyc_id": kyc_id_str,
            "status": kyc.status.value,
            "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None
        },
        message="KYC submitted successfully. Your verification is under review."
    )


@router.get("/status", response_model=ResponseModel)
def get_kyc_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get KYC status with all field variations"""
    # KYC.user_id and current_user.id are String(36)
    kyc = db.query(KYC).filter(KYC.user_id == str(current_user.id)).first()
    
    kyc_status_value = current_user.kyc_status.value if hasattr(current_user.kyc_status, 'value') else str(current_user.kyc_status)
    is_kyc_verified = kyc_status_value == "verified"
    
    if not kyc:
        return ResponseModel(
            success=True,
            data={
                "kyc_status": kyc_status_value,
                "kycStatus": kyc_status_value,  # camelCase alternative
                "is_kyc_verified": is_kyc_verified,  # Boolean alternative
                "kyc_id": None,
                "submitted_at": None,
                "verified_at": current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None,
                "rejection_reason": None,
                "notes": None
            }
        )
    
    return ResponseModel(
        success=True,
        data={
            "kyc_status": kyc.status.value,
            "kycStatus": kyc.status.value,  # camelCase alternative
            "is_kyc_verified": kyc.status.value == "verified",  # Boolean alternative
            "kyc_id": str(kyc.id) if kyc.id else None,
            "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
            "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
            "rejection_reason": kyc.rejection_reason if hasattr(kyc, 'rejection_reason') else None,
            "notes": None  # Can be added to KYC model if needed
        }
    )


@router.post("/skip", response_model=ResponseModel)
def skip_kyc(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Skip KYC submission - user can complete later from profile"""
    # User's kyc_status remains "not_verified" (default)
    # No action needed, just return success message
    
    return ResponseModel(
        success=True,
        message="KYC can be completed later from your profile"
    )

