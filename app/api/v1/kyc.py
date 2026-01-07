from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.kyc import GSTVerify, GSTVerifyResponse, KYCSubmit, KYCResponse, KYCStatusResponse
from app.schemas.common import ResponseModel
from app.models.kyc import KYC, KYCStatus
from app.models.user import User
from app.utils.gst_verification import verify_gst_number

router = APIRouter()


@router.post("/verify-gst", response_model=ResponseModel)
def verify_gst(gst_data: GSTVerify, db: Session = Depends(get_db)):
    """Verify GST number"""
    gst_details = verify_gst_number(gst_data.gst_number)
    
    if not gst_details:
        raise HTTPException(status_code=400, detail="Invalid GST number")
    
    return ResponseModel(
        success=True,
        data=GSTVerifyResponse(**gst_details)
    )


@router.post("/submit", response_model=ResponseModel, status_code=201)
def submit_kyc(
    kyc_data: KYCSubmit,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit business KYC"""
    # Check if KYC already exists (handle UUID conversion)
    existing_kyc = db.query(KYC).filter(KYC.user_id == str(current_user.id)).first()
    
    if existing_kyc and existing_kyc.status == KYCStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="KYC already verified")
    
    # Verify GST
    gst_details = verify_gst_number(kyc_data.gst_number)
    if not gst_details:
        raise HTTPException(status_code=400, detail="Invalid GST number")
    
    if existing_kyc:
        # Update existing KYC
        existing_kyc.business_name = kyc_data.business_name
        existing_kyc.gst_number = kyc_data.gst_number
        existing_kyc.pan_number = kyc_data.pan_number
        existing_kyc.business_type = kyc_data.business_type
        existing_kyc.address = kyc_data.address
        existing_kyc.documents = kyc_data.documents
        existing_kyc.status = KYCStatus.PENDING
        db.commit()
        db.refresh(existing_kyc)
        kyc = existing_kyc
    else:
        # Create new KYC (handle UUID conversion - User.id is String(36), KYC.user_id is UUID)
        from uuid import UUID
        try:
            user_uuid = UUID(str(current_user.id))
        except (ValueError, AttributeError):
            # If conversion fails, try without dashes
            user_uuid = UUID(str(current_user.id).replace('-', ''))
        kyc = KYC(
            user_id=user_uuid,
            business_name=kyc_data.business_name,
            gst_number=kyc_data.gst_number,
            pan_number=kyc_data.pan_number,
            business_type=kyc_data.business_type,
            address=kyc_data.address,
            documents=kyc_data.documents,
            status=KYCStatus.PENDING
        )
        db.add(kyc)
        db.commit()
        db.refresh(kyc)
    
    # Update user KYC status
    from app.models.user import KYCStatus as UserKYCStatus
    current_user.kyc_status = UserKYCStatus.PENDING
    db.commit()
    
    return ResponseModel(
        success=True,
        data={
            "kyc_id": str(kyc.id),
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
    
    return ResponseModel(
        success=True,
        data={
            "kyc_status": kyc.status.value,
            "kycStatus": kyc.status.value,  # camelCase alternative
            "is_kyc_verified": kyc.status.value == "verified",  # Boolean alternative
            "kyc_id": kyc.id,
            "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
            "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
            "rejection_reason": kyc.rejection_reason if hasattr(kyc, 'rejection_reason') else None,
            "notes": None  # Can be added to KYC model if needed
        }
    )

