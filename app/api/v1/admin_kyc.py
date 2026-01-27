"""
Admin KYC Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, String, cast
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.admin_kyc import KYCVerify, KYCReject
from app.models.user import User, KYCStatus as UserKYCStatus
from app.models.kyc import KYC, KYCStatus
from app.models.kyc_document import KYCDocument
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.models.admin import Admin

router = APIRouter()


@router.post("/sync-user-statuses", response_model=ResponseModel)
async def sync_user_kyc_statuses(
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """
    Manually sync user kyc_status from verified KYC submissions.
    This is a utility endpoint to fix users whose profile kyc_status doesn't match their KYC submission status.
    """
    try:
        # Find all verified KYC submissions
        verified_kycs = db.query(KYC).filter(
            or_(
                KYC.status == KYCStatus.VERIFIED,
                cast(KYC.status, String) == 'verified',
                cast(KYC.status, String) == 'VERIFIED'
            )
        ).all()
        
        updated_count = 0
        for kyc in verified_kycs:
            # Get the user
            user = kyc.user
            if not user:
                continue
            
            # Check if user's kyc_status needs updating
            user_status = user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status)
            if user_status.lower() != 'verified':
                # Update user's kyc_status to verified
                db.query(User).filter(User.id == user.id).update({
                    "kyc_status": UserKYCStatus.VERIFIED.value,
                    "kyc_verified_at": kyc.verified_at if kyc.verified_at else datetime.utcnow()
                })
                updated_count += 1
        
        # Find all rejected KYC submissions
        rejected_kycs = db.query(KYC).filter(
            or_(
                KYC.status == KYCStatus.REJECTED,
                cast(KYC.status, String) == 'rejected',
                cast(KYC.status, String) == 'REJECTED'
            )
        ).all()
        
        rejected_count = 0
        for kyc in rejected_kycs:
            user = kyc.user
            if not user:
                continue
            
            user_status = user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status)
            if user_status.lower() != 'rejected':
                db.query(User).filter(User.id == user.id).update({
                    "kyc_status": UserKYCStatus.REJECTED.value
                })
                rejected_count += 1
        
        db.commit()
        
        return ResponseModel(
            success=True,
            data={
                "verified_users_updated": updated_count,
                "rejected_users_updated": rejected_count,
                "total_updated": updated_count + rejected_count
            },
            message=f"Synced {updated_count + rejected_count} user profiles with their KYC submission status"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync user statuses: {str(e)}"
        )


@router.get("", response_model=ResponseModel)
async def list_kyc_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List KYC submissions"""
    # Note: KYC.user_id is UUID, but User.id is String(36)
    # We need to query KYC and join with User
    query = db.query(KYC).options(joinedload(KYC.user))
    
    # Apply status filter
    if status:
        try:
            kyc_status = KYCStatus(status)
            query = query.filter(KYC.status == kyc_status)
        except ValueError:
            pass
    
    # Apply search filter
    if search:
        # Use join to search across both KYC and User tables
        # Note: KYC.user_id is UUID, User.id is String(36), but relationship should work
        query = query.join(User).filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                KYC.business_name.ilike(f"%{search}%"),
                KYC.gst_number.ilike(f"%{search}%"),
                # New primary field
                KYC.fssai_number.ilike(f"%{search}%"),
                # Legacy support (old records)
                KYC.pan_number.ilike(f"%{search}%")
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    kyc_submissions = query.order_by(KYC.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response with all field name variations
    submissions = []
    for kyc in kyc_submissions:
        user = kyc.user
        if not user:
            continue
        
        # Get KYC documents
        # Note: KYCDocument.user_id is UUID, User.id is String(36)
        # Use cast to convert UUID to string for comparison
        documents = db.query(KYCDocument).filter(
            cast(KYCDocument.user_id, String) == str(user.id)
        ).all()
        
        submission_data = {
            "id": str(kyc.id),
            "userId": str(kyc.user_id),
            "user_id": str(kyc.user_id),
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone
            },
            "userName": user.name,
            "user_name": user.name,
            "email": user.email,
            "phone": user.phone,
            "businessName": kyc.business_name,
            "business_name": kyc.business_name,
            "companyName": kyc.business_name,
            "gstNumber": kyc.gst_number,
            "gst_number": kyc.gst_number,
            "gst": kyc.gst_number,
            "fssaiNumber": kyc.fssai_number,
            "fssai_number": kyc.fssai_number,
            "fssai": kyc.fssai_number,
            "status": kyc.status.value,
            "kyc_status": kyc.status.value,
            "submittedAt": kyc.created_at.isoformat() if kyc.created_at else None,
            "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
            "submissionDate": kyc.created_at.isoformat() if kyc.created_at else None,
            "submission_date": kyc.created_at.isoformat() if kyc.created_at else None,
            "createdAt": kyc.created_at.isoformat() if kyc.created_at else None,
            "created_at": kyc.created_at.isoformat() if kyc.created_at else None,
            "verifiedAt": kyc.verified_at.isoformat() if kyc.verified_at else None,
            "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
            "rejectedAt": None,  # KYC model doesn't have rejected_at, use status
            "rejected_at": None,
            "rejectionReason": None,  # KYC model doesn't have rejection_reason field
            "rejection_reason": None,
            "verifiedBy": str(user.kyc_verified_by) if user.kyc_verified_by else None,
            "verified_by": str(user.kyc_verified_by) if user.kyc_verified_by else None
        }
        
        # Add rejection info if status is rejected
        if kyc.status == KYCStatus.REJECTED:
            # Check user's kyc_status for rejection reason if available
            if hasattr(user, 'kyc_status') and user.kyc_status == UserKYCStatus.REJECTED:
                # Rejection reason might be in user model or KYC model
                # For now, set a default message
                submission_data["rejectionReason"] = "KYC submission rejected"
                submission_data["rejection_reason"] = "KYC submission rejected"
                submission_data["rejectedAt"] = user.updated_at.isoformat() if user.updated_at else None
                submission_data["rejected_at"] = user.updated_at.isoformat() if user.updated_at else None
        
        submissions.append(submission_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": submissions,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        },
        message="KYC submissions retrieved successfully"
    )


@router.get("/user/{user_id}", response_model=ResponseModel)
async def get_kyc_by_user_id(
    user_id: str,  # Accept as string to handle both UUID formats
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get KYC submission by user ID"""
    # Handle both dashed and non-dashed UUID formats
    user_id_str = str(user_id).replace('-', '').strip() if '-' in str(user_id) else str(user_id).strip()
    
    # First, verify user exists
    user = db.query(User).filter(
        or_(
            User.id == str(user_id),
            User.id == user_id_str
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Query KYC by user_id
    # Note: KYC.user_id is UUID, User.id is String(36)
    # Convert user.id to UUID for comparison
    try:
        from uuid import UUID as UUIDType
        user_uuid = UUIDType(str(user.id))
        # Get the most recent KYC submission for this user
        kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
            KYC.user_id == user_uuid
        ).order_by(KYC.created_at.desc()).first()
    except (ValueError, AttributeError):
        # If UUID conversion fails, try using cast
        kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
            cast(KYC.user_id, String) == str(user.id)
        ).order_by(KYC.created_at.desc()).first()
    
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found for this user")
    
    # Format response with all field name variations
    kyc_data = {
        "id": str(kyc.id),
        "userId": str(kyc.user_id),
        "user_id": str(kyc.user_id),
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        },
        "userName": user.name,
        "user_name": user.name,
        "email": user.email,
        "phone": user.phone,
        "businessName": kyc.business_name,
        "business_name": kyc.business_name,
        "companyName": kyc.business_name,
        "gstNumber": kyc.gst_number,
        "gst_number": kyc.gst_number,
        "gst": kyc.gst_number,
        "fssaiNumber": kyc.fssai_number,
        "fssai_number": kyc.fssai_number,
        "fssai": kyc.fssai_number,
        "status": kyc.status.value if hasattr(kyc.status, 'value') else str(kyc.status),
        "kyc_status": kyc.status.value if hasattr(kyc.status, 'value') else str(kyc.status),
        "submittedAt": kyc.created_at.isoformat() if kyc.created_at else None,
        "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "submissionDate": kyc.created_at.isoformat() if kyc.created_at else None,
        "submission_date": kyc.created_at.isoformat() if kyc.created_at else None,
        "createdAt": kyc.created_at.isoformat() if kyc.created_at else None,
        "created_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "verifiedAt": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "rejectedAt": None,
        "rejected_at": None,
        "rejectionReason": None,
        "rejection_reason": None,
        "verifiedBy": str(user.kyc_verified_by) if hasattr(user, 'kyc_verified_by') and user.kyc_verified_by else None,
        "verified_by": str(user.kyc_verified_by) if hasattr(user, 'kyc_verified_by') and user.kyc_verified_by else None
    }
    
    # Add rejection info if status is rejected
    if kyc.status == KYCStatus.REJECTED:
        # Check user's kyc_status for rejection reason if available
        if hasattr(user, 'kyc_status') and user.kyc_status == UserKYCStatus.REJECTED:
            # Rejection reason might be in user model or KYC model
            # For now, set a default message
            kyc_data["rejectionReason"] = "KYC submission rejected"
            kyc_data["rejection_reason"] = "KYC submission rejected"
            kyc_data["rejectedAt"] = user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
            kyc_data["rejected_at"] = user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
    
    return ResponseModel(
        success=True,
        data=kyc_data,
        message="KYC submission retrieved successfully"
    )


@router.get("/{kyc_id}", response_model=ResponseModel)
async def get_kyc_details(
    kyc_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get KYC submission details"""
    # Convert UUID to string for comparison (handles type mismatch)
    kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
        cast(KYC.id, String) == str(kyc_id)
    ).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    user = kyc.user
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this KYC submission")
    
    # Get KYC documents
    # Note: KYCDocument.user_id is UUID, User.id is String(36)
    # Use cast to convert UUID to string for comparison
    documents = db.query(KYCDocument).filter(
        cast(KYCDocument.user_id, String) == str(user.id)
    ).all()
    
    # Format address
    address = kyc.address if isinstance(kyc.address, dict) else {}
    
    # Format additional info
    additional_info = {
        "businessType": kyc.business_type,
        "business_type": kyc.business_type
    }
    
    kyc_data = {
        "id": str(kyc.id),
        "userId": str(kyc.user_id),
        "user_id": str(kyc.user_id),
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        },
        "userName": user.name,
        "user_name": user.name,
        "email": user.email,
        "phone": user.phone,
        "businessName": kyc.business_name,
        "business_name": kyc.business_name,
        "companyName": kyc.business_name,
        "gstNumber": kyc.gst_number,
        "gst_number": kyc.gst_number,
        "gst": kyc.gst_number,
        "fssaiNumber": kyc.fssai_number,
        "fssai_number": kyc.fssai_number,
        "fssai": kyc.fssai_number,
        "status": kyc.status.value,
        "kyc_status": kyc.status.value,
        "submittedAt": kyc.created_at.isoformat() if kyc.created_at else None,
        "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "submissionDate": kyc.created_at.isoformat() if kyc.created_at else None,
        "submission_date": kyc.created_at.isoformat() if kyc.created_at else None,
        "createdAt": kyc.created_at.isoformat() if kyc.created_at else None,
        "created_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "verifiedAt": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "rejectedAt": None,
        "rejected_at": None,
        "rejectionReason": None,
        "rejection_reason": None,
        "verifiedBy": str(user.kyc_verified_by) if user.kyc_verified_by else None,
        "verified_by": str(user.kyc_verified_by) if user.kyc_verified_by else None,
        "address": address,
        "additionalInfo": additional_info
    }
    
    return ResponseModel(
        success=True,
        data=kyc_data,
        message="KYC submission retrieved successfully"
    )


@router.put("/{kyc_id}/verify", response_model=ResponseModel)
async def verify_kyc(
    kyc_id: UUID,
    verify_data: KYCVerify,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Verify KYC submission"""
    # Convert UUID to string for comparison (handles type mismatch)
    kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
        cast(KYC.id, String) == str(kyc_id)
    ).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    if kyc.status != KYCStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"KYC is already {kyc.status.value}")
    
    # Get user before updates (needed for transaction)
    user = kyc.user
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this KYC submission")
    
    try:
        # Use a transaction to ensure both updates succeed or fail together
        # Update KYC status using update() to avoid type mismatch in WHERE clause
        db.query(KYC).filter(
            cast(KYC.id, String) == str(kyc_id)
        ).update({
            "status": KYCStatus.VERIFIED,
            "verified_at": datetime.utcnow()
        })
        
        # Update user's KYC status using update() to ensure proper enum handling
        # This is CRITICAL: The mobile app checks users.kyc_status, not kycs.status
        db.query(User).filter(User.id == user.id).update({
            "kyc_status": UserKYCStatus.VERIFIED.value,  # Use .value to get the string "verified"
            "kyc_verified_at": datetime.utcnow(),
            "kyc_verified_by": str(admin.id)
        })
        
        # Commit both updates together (atomic transaction)
        db.commit()
        
        # Reload objects to get updated values
        db.refresh(kyc)
        db.refresh(user)
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify KYC: {str(e)}"
        )
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="kyc_verified",
        entity_type="kyc",
        entity_id=kyc_id,
        details={"comments": verify_data.comments},
        request=request
    )
    
    # Return success with updated status info
    return ResponseModel(
        success=True,
        data={
            "kyc_id": str(kyc_id),
            "kyc_status": kyc.status.value,
            "user_kyc_status": user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status),
            "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None
        },
        message="KYC verified successfully. User profile has been updated."
    )


@router.put("/{kyc_id}/reject", response_model=ResponseModel)
async def reject_kyc(
    kyc_id: UUID,
    reject_data: KYCReject,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Reject KYC submission"""
    # Convert UUID to string for comparison (handles type mismatch)
    kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
        cast(KYC.id, String) == str(kyc_id)
    ).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    if kyc.status != KYCStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"KYC is already {kyc.status.value}")
    
    if not reject_data.reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    # Get user before updates (needed for transaction)
    user = kyc.user
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this KYC submission")
    
    try:
        # Use a transaction to ensure both updates succeed or fail together
        # Update KYC status using update() to avoid type mismatch in WHERE clause
        db.query(KYC).filter(
            cast(KYC.id, String) == str(kyc_id)
        ).update({
            "status": KYCStatus.REJECTED
        })
        
        # Update user's KYC status using update() to ensure proper enum handling
        # This is CRITICAL: The mobile app checks users.kyc_status, not kycs.status
        db.query(User).filter(User.id == user.id).update({
            "kyc_status": UserKYCStatus.REJECTED.value  # Use .value to get the string "rejected"
        })
        
        # Commit both updates together (atomic transaction)
        db.commit()
        
        # Reload objects to get updated values
        db.refresh(kyc)
        db.refresh(user)
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject KYC: {str(e)}"
        )
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="kyc_rejected",
        entity_type="kyc",
        entity_id=kyc_id,
        details={"reason": reject_data.reason},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="KYC rejected successfully"
    )


@router.get("/{kyc_id}/documents", response_model=ResponseModel)
async def get_kyc_documents(
    kyc_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get KYC documents"""
    # Convert UUID to string for comparison (handles type mismatch)
    kyc = db.query(KYC).options(joinedload(KYC.user)).filter(
        cast(KYC.id, String) == str(kyc_id)
    ).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    user = kyc.user
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this KYC submission")
    
    # Get KYC documents
    # Note: KYCDocument.user_id is UUID, User.id is String(36)
    # Use cast to convert UUID to string for comparison
    documents = db.query(KYCDocument).filter(
        cast(KYCDocument.user_id, String) == str(user.id)
    ).all()
    
    # Format documents
    document_list = []
    for doc in documents:
        # Map document types
        doc_type_map = {
            "gst_certificate": "GST Certificate",
            "pan_card": "PAN Card",
            "business_license": "Business License",
            "other": "Other Document"
        }
        doc_name = doc_type_map.get(doc.document_type, doc.document_type.replace("_", " ").title())
        
        document_list.append({
            "id": str(doc.id),
            "type": doc.document_type,
            "name": doc_name,
            "url": doc.document_url,
            "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        })
    
    # Also check if documents are stored in KYC.documents JSON field
    if kyc.documents and isinstance(kyc.documents, dict):
        for doc_key, doc_url in kyc.documents.items():
            if isinstance(doc_url, str) and doc_url:
                document_list.append({
                    "id": f"kyc-{doc_key}",
                    "type": doc_key,
                    "name": doc_key.replace("_", " ").title(),
                    "url": doc_url,
                    "uploadedAt": kyc.created_at.isoformat() if kyc.created_at else None,
                    "uploaded_at": kyc.created_at.isoformat() if kyc.created_at else None
                })
    
    return ResponseModel(
        success=True,
        data=document_list,
        message="KYC documents retrieved successfully"
    )

