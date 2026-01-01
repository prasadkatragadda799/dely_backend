"""
Admin KYC Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.user import User, KYCStatus
from app.models.kyc_document import KYCDocument
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.models.admin import Admin

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_kyc_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List KYC submissions"""
    query = db.query(User).filter(User.kyc_status != None)
    
    # Apply status filter
    if status:
        try:
            kyc_status = KYCStatus(status)
            query = query.filter(User.kyc_status == kyc_status)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    # Format response
    submissions = []
    for user in users:
        # Get KYC documents
        documents = db.query(KYCDocument).filter(KYCDocument.user_id == user.id).all()
        
        submissions.append({
            "id": user.id,
            "user": {
                "id": user.id,
                "name": user.name,
                "businessName": user.business_name,
                "email": user.email
            },
            "gstNumber": user.gst_number,
            "panNumber": user.pan_number,
            "status": user.kyc_status.value,
            "submissionDate": user.created_at,  # Or use a dedicated KYC submission date
            "documents": [{
                "type": doc.document_type,
                "url": doc.document_url
            } for doc in documents]
        })
    
    return ResponseModel(
        success=True,
        data={
            "submissions": submissions,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        },
        message="KYC submissions retrieved successfully"
    )


@router.put("/{user_id}/verify", response_model=ResponseModel)
async def verify_kyc(
    user_id: UUID,
    verify_data: dict,  # {"comments": "..."}
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Verify KYC submission"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status == KYCStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="KYC is already verified")
    
    user.kyc_status = KYCStatus.VERIFIED
    user.kyc_verified_at = datetime.utcnow()
    user.kyc_verified_by = admin.id
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="kyc_verified",
        entity_type="user",
        entity_id=user_id,
        details={"comments": verify_data.get("comments")},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": user.id,
            "kycStatus": user.kyc_status.value,
            "verifiedAt": user.kyc_verified_at
        },
        message="KYC verified successfully"
    )


@router.put("/{user_id}/reject", response_model=ResponseModel)
async def reject_kyc(
    user_id: UUID,
    reject_data: dict,  # {"reason": "..."}
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Reject KYC submission"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status == KYCStatus.REJECTED:
        raise HTTPException(status_code=400, detail="KYC is already rejected")
    
    user.kyc_status = KYCStatus.REJECTED
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="kyc_rejected",
        entity_type="user",
        entity_id=user_id,
        details={"reason": reject_data.get("reason")},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": user.id,
            "kycStatus": user.kyc_status.value
        },
        message="KYC rejected successfully"
    )

