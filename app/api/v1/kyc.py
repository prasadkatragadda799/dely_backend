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
    # Check if KYC already exists
    existing_kyc = db.query(KYC).filter(KYC.user_id == current_user.id).first()
    
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
        # Create new KYC
        kyc = KYC(
            user_id=current_user.id,
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
    current_user.kyc_status = KYCStatus.PENDING
    db.commit()
    
    return ResponseModel(
        success=True,
        data={
            "kyc_status": kyc.status.value,
            "kyc_id": kyc.id
        },
        message="KYC submitted successfully"
    )


@router.get("/status", response_model=ResponseModel)
def get_kyc_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get KYC status"""
    kyc = db.query(KYC).filter(KYC.user_id == current_user.id).first()
    
    if not kyc:
        return ResponseModel(
            success=True,
            data=KYCStatusResponse(
                kyc_status=current_user.kyc_status.value,
                kyc_id=None,
                verified_at=None
            )
        )
    
    return ResponseModel(
        success=True,
        data=KYCStatusResponse(
            kyc_status=kyc.status.value,
            kyc_id=kyc.id,
            verified_at=kyc.verified_at
        )
    )

