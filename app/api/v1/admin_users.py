"""
Admin User Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.user import User, KYCStatus
from app.models.order import Order
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.models.admin import Admin

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    kyc_status: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort: Optional[str] = Query("created_at", pattern="^(name|email|created_at)$"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all users with filters"""
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.business_name.ilike(f"%{search}%"),
                User.gst_number.ilike(f"%{search}%")
            )
        )
    
    if kyc_status:
        try:
            kyc_status_enum = KYCStatus(kyc_status)
            query = query.filter(User.kyc_status == kyc_status_enum)
        except ValueError:
            pass
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Apply sorting
    if sort == "name":
        order_by = User.name.asc() if order == "asc" else User.name.desc()
    elif sort == "email":
        order_by = User.email.asc() if order == "asc" else User.email.desc()
    else:
        order_by = User.created_at.desc() if order == "desc" else User.created_at.asc()
    
    query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    # Format response with order stats
    user_list = []
    for u in users:
        # Get order statistics
        total_orders = db.query(func.count(Order.id)).filter(Order.user_id == u.id).scalar() or 0
        total_spent = db.query(func.sum(Order.total_amount)).filter(Order.user_id == u.id).scalar() or 0
        
        user_data = {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "businessName": u.business_name,
            "gstNumber": u.gst_number,
            "kycStatus": u.kyc_status.value,
            "isActive": u.is_active,
            "totalOrders": total_orders,
            "totalSpent": float(total_spent) if total_spent else 0.0,
            "createdAt": u.created_at
        }
        user_list.append(user_data)
    
    return ResponseModel(
        success=True,
        data={
            "users": user_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        },
        message="Users retrieved successfully"
    )


@router.get("/{user_id}", response_model=ResponseModel)
async def get_user(
    user_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get KYC documents
    kyc_documents = []
    for doc in user.kyc_documents:
        kyc_documents.append({
            "type": doc.document_type,
            "url": doc.document_url,
            "uploadedAt": doc.uploaded_at
        })
    
    # Get recent orders
    recent_orders = db.query(Order).filter(
        Order.user_id == user_id
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "businessName": user.business_name,
        "gstNumber": user.gst_number,
        "panNumber": user.pan_number,
        "kycStatus": user.kyc_status.value,
        "kycDocuments": kyc_documents,
        "addresses": user.delivery_locations if hasattr(user, 'delivery_locations') else [],
        "orders": [{
            "id": o.id,
            "orderNumber": o.order_number,
            "status": o.status.value,
            "totalAmount": float(o.total_amount),
            "createdAt": o.created_at
        } for o in recent_orders],
        "createdAt": user.created_at
    }
    
    return ResponseModel(
        success=True,
        data=user_data,
        message="User retrieved successfully"
    )


@router.put("/{user_id}/block", response_model=ResponseModel)
async def block_user(
    user_id: UUID,
    block_data: dict,  # {"isActive": false, "reason": "..."}
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Block or unblock a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    is_active = block_data.get("isActive", not user.is_active)
    user.is_active = is_active
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="user_blocked" if not is_active else "user_unblocked",
        entity_type="user",
        entity_id=user_id,
        details={
            "isActive": is_active,
            "reason": block_data.get("reason")
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={"isActive": is_active},
        message=f"User {'blocked' if not is_active else 'unblocked'} successfully"
    )

