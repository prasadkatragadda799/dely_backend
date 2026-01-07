"""
Admin User Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, String, cast
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.user import User, KYCStatus
from app.models.order import Order
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.email import send_password_reset_email
from app.utils.security import get_password_hash
from app.models.admin import Admin
import secrets

router = APIRouter()


class BlockUserRequest(BaseModel):
    isActive: Optional[bool] = None
    is_active: Optional[bool] = None  # Alternative field name
    reason: Optional[str] = None


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_number: Optional[str] = None  # Alternative field name
    business_name: Optional[str] = None
    businessName: Optional[str] = None  # Alternative field name
    gst_number: Optional[str] = None
    gstNumber: Optional[str] = None  # Alternative field name
    is_active: Optional[bool] = None
    isActive: Optional[bool] = None  # Alternative field name


@router.get("", response_model=ResponseModel)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    kyc_status: Optional[str] = Query(None, alias="kycStatus"),  # Support both formats
    kycStatus: Optional[str] = None,  # camelCase support
    is_active: Optional[bool] = Query(None, alias="isActive"),  # Support both formats
    isActive: Optional[bool] = None,  # camelCase support
    sort: Optional[str] = Query("createdAt", pattern="^(name|email|createdAt|created_at|totalOrders|total_orders)$"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all users with filters"""
    query = db.query(User)
    
    # Normalize query parameters (support both formats)
    kyc_status_filter = kycStatus or kyc_status
    is_active_filter = isActive if isActive is not None else is_active
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),  # Added phone search
                User.business_name.ilike(f"%{search}%"),
                User.gst_number.ilike(f"%{search}%")
            )
        )
    
    if kyc_status_filter:
        try:
            kyc_status_enum = KYCStatus(kyc_status_filter.lower())
            query = query.filter(User.kyc_status == kyc_status_enum)
        except ValueError:
            pass
    
    if is_active_filter is not None:
        query = query.filter(User.is_active == is_active_filter)
    
    # Apply sorting
    if sort == "name":
        order_by = User.name.asc() if order == "asc" else User.name.desc()
        query = query.order_by(order_by)
    elif sort == "email":
        order_by = User.email.asc() if order == "asc" else User.email.desc()
        query = query.order_by(order_by)
    elif sort in ["totalOrders", "total_orders"]:
        # Sort by total orders using subquery
        # Note: Order.user_id is String(36), User.id is String(36), so direct comparison should work
        order_count_subq = db.query(
            Order.user_id,
            func.count(Order.id).label('order_count')
        ).group_by(Order.user_id).subquery()
        
        # Direct join - both are String(36) so should work
        query = query.outerjoin(order_count_subq, User.id == order_count_subq.c.user_id)
        if order == "asc":
            order_by = func.coalesce(order_count_subq.c.order_count, 0).asc()
        else:
            order_by = func.coalesce(order_count_subq.c.order_count, 0).desc()
        query = query.order_by(order_by)
    else:
        # Default: sort by created_at (support both createdAt and created_at)
        order_by = User.created_at.desc() if order == "desc" else User.created_at.asc()
        query = query.order_by(order_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    # Format response with order stats and all field name variations
    user_list = []
    for u in users:
        # Get order statistics
        total_orders = db.query(func.count(Order.id)).filter(Order.user_id == str(u.id)).scalar() or 0
        total_spent = db.query(func.sum(Order.total_amount)).filter(Order.user_id == str(u.id)).scalar() or 0
        
        # Format dates
        created_at_iso = u.created_at.isoformat() if u.created_at else None
        
        user_data = {
            "id": str(u.id),  # Ensure string format
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "phoneNumber": u.phone,  # Alternative field name
            "business_name": u.business_name,
            "businessName": u.business_name,  # Alternative field name
            "companyName": u.business_name,  # Alternative field name
            "gst_number": u.gst_number,
            "gstNumber": u.gst_number,  # Alternative field name
            "gst": u.gst_number,  # Alternative field name
            "kyc_status": u.kyc_status.value if hasattr(u.kyc_status, 'value') else (str(u.kyc_status) if u.kyc_status else "not_verified"),
            "kycStatus": u.kyc_status.value if hasattr(u.kyc_status, 'value') else (str(u.kyc_status) if u.kyc_status else "not_verified"),  # Alternative field name
            "is_active": u.is_active,
            "isActive": u.is_active,  # Alternative field name
            "total_orders": total_orders,
            "totalOrders": total_orders,  # Alternative field name
            "ordersCount": total_orders,  # Alternative field name
            "total_spent": float(total_spent) if total_spent else 0.0,
            "totalSpent": float(total_spent) if total_spent else 0.0,  # Alternative field name
            "lifetimeValue": float(total_spent) if total_spent else 0.0,  # Alternative field name
            "created_at": created_at_iso,
            "createdAt": created_at_iso,  # Alternative field name
            "registeredDate": created_at_iso,  # Alternative field name
            "registered_date": created_at_iso,  # Alternative field name
            "avatar": None  # Not implemented yet
        }
        user_list.append(user_data)
    
    return ResponseModel(
        success=True,
        data={
            "items": user_list,  # Use "items" key as per requirements
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 0
            }
        },
        message="Users retrieved successfully"
    )


@router.get("/{user_id}", response_model=ResponseModel)
async def get_user(
    user_id: str,  # Accept as string to handle both UUID formats
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get user details"""
    # Handle both dashed and non-dashed UUID formats
    user_id_str = str(user_id).replace('-', '').strip() if '-' in str(user_id) else str(user_id).strip()
    
    # Try to find user by ID (handle both formats)
    user = db.query(User).filter(
        or_(
            User.id == str(user_id),
            User.id == user_id_str
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get order statistics
    total_orders = db.query(func.count(Order.id)).filter(Order.user_id == str(user.id)).scalar() or 0
    total_spent = db.query(func.sum(Order.total_amount)).filter(Order.user_id == str(user.id)).scalar() or 0
    
    # Get KYC documents
    kyc_documents = []
    for doc in user.kyc_documents:
        kyc_documents.append({
            "type": doc.document_type,
            "url": doc.document_url,
            "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        })
    
    # Get recent orders
    recent_orders = db.query(Order).filter(
        Order.user_id == str(user.id)
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # Format address from JSON if available
    address_dict = {}
    if user.address and isinstance(user.address, dict):
        address_dict = {
            "street": user.address.get("address") or user.address.get("business_address") or user.address.get("street"),
            "city": user.address.get("city") or user.address.get("business_city"),
            "state": user.address.get("state") or user.address.get("business_state"),
            "pincode": user.address.get("pincode") or user.address.get("business_pincode")
        }
    
    # Format delivery locations
    delivery_locations = []
    if hasattr(user, 'delivery_locations') and user.delivery_locations:
        for loc in user.delivery_locations:
            delivery_locations.append({
                "id": str(loc.id),
                "address_line1": loc.address,
                "address_line2": loc.landmark,
                "city": loc.city,
                "state": loc.state,
                "pincode": loc.pincode,
                "type": loc.type,
                "is_default": loc.is_default
            })
    
    user_data = {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "phoneNumber": user.phone,  # Alternative field name
        "business_name": user.business_name,
        "businessName": user.business_name,  # Alternative field name
        "gst_number": user.gst_number,
        "gstNumber": user.gst_number,  # Alternative field name
        "pan_number": user.pan_number,
        "panNumber": user.pan_number,  # Alternative field name
        "kyc_status": user.kyc_status.value if hasattr(user.kyc_status, 'value') else (str(user.kyc_status) if user.kyc_status else "not_verified"),
        "kycStatus": user.kyc_status.value if hasattr(user.kyc_status, 'value') else (str(user.kyc_status) if user.kyc_status else "not_verified"),  # Alternative field name
        "is_active": user.is_active,
        "isActive": user.is_active,  # Alternative field name
        "total_orders": total_orders,
        "totalOrders": total_orders,  # Alternative field name
        "total_spent": float(total_spent) if total_spent else 0.0,
        "totalSpent": float(total_spent) if total_spent else 0.0,  # Alternative field name
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "createdAt": user.created_at.isoformat() if user.created_at else None,  # Alternative field name
        "address": address_dict if address_dict else None,
        "kycDocuments": kyc_documents,
        "addresses": delivery_locations,
        "orders": [{
            "id": str(o.id),
            "orderNumber": o.order_number,
            "status": o.status.value,
            "totalAmount": float(o.total_amount) if o.total_amount else 0.0,
            "createdAt": o.created_at.isoformat() if o.created_at else None
        } for o in recent_orders]
    }
    
    return ResponseModel(
        success=True,
        data=user_data,
        message="User retrieved successfully"
    )


@router.put("/{user_id}", response_model=ResponseModel)
async def update_user(
    user_id: str,  # Accept as string to handle both UUID formats
    user_data: AdminUserUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update user details"""
    # Handle both dashed and non-dashed UUID formats
    user_id_str = str(user_id).replace('-', '').strip() if '-' in str(user_id) else str(user_id).strip()
    
    # Try to find user by ID (handle both formats)
    user = db.query(User).filter(
        or_(
            User.id == str(user_id),
            User.id == user_id_str
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields (support both camelCase and snake_case)
    if user_data.name is not None:
        user.name = user_data.name
    
    if user_data.email is not None:
        # Check if email already exists
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.id != str(user.id)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_data.email
    
    phone_to_update = user_data.phone_number or user_data.phone
    if phone_to_update is not None:
        # Check if phone already exists
        existing_user = db.query(User).filter(
            User.phone == phone_to_update,
            User.id != str(user.id)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Phone number already in use")
        user.phone = phone_to_update
    
    business_name_to_update = user_data.businessName or user_data.business_name
    if business_name_to_update is not None:
        user.business_name = business_name_to_update
    
    gst_to_update = user_data.gstNumber or user_data.gst_number
    if gst_to_update is not None:
        user.gst_number = gst_to_update
    
    is_active_to_update = user_data.isActive if user_data.isActive is not None else user_data.is_active
    if is_active_to_update is not None:
        user.is_active = is_active_to_update
    
    db.commit()
    db.refresh(user)
    
    # Log activity
    try:
        user_uuid = UUID(str(user.id))
    except (ValueError, AttributeError):
        user_uuid = None
    
    if user_uuid:
        log_admin_activity(
            db=db,
            admin_id=admin.id,
            action="user_updated",
            entity_type="user",
            entity_id=user_uuid,
            details={
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active
            },
            request=request
        )
    
    # Return updated user data
    total_orders = db.query(func.count(Order.id)).filter(Order.user_id == str(user.id)).scalar() or 0
    total_spent = db.query(func.sum(Order.total_amount)).filter(Order.user_id == str(user.id)).scalar() or 0
    
    user_response = {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "phoneNumber": user.phone,
        "business_name": user.business_name,
        "businessName": user.business_name,
        "gst_number": user.gst_number,
        "gstNumber": user.gst_number,
        "kyc_status": user.kyc_status.value if hasattr(user.kyc_status, 'value') else (str(user.kyc_status) if user.kyc_status else "not_verified"),
        "kycStatus": user.kyc_status.value if hasattr(user.kyc_status, 'value') else (str(user.kyc_status) if user.kyc_status else "not_verified"),
        "is_active": user.is_active,
        "isActive": user.is_active,
        "total_orders": total_orders,
        "totalOrders": total_orders,
        "total_spent": float(total_spent) if total_spent else 0.0,
        "totalSpent": float(total_spent) if total_spent else 0.0,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "createdAt": user.created_at.isoformat() if user.created_at else None
    }
    
    return ResponseModel(
        success=True,
        data=user_response,
        message="User updated successfully"
    )


@router.put("/{user_id}/block", response_model=ResponseModel)
async def block_user(
    user_id: str,  # Accept as string to handle both UUID formats
    block_data: BlockUserRequest,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Block or unblock a user"""
    # Handle both dashed and non-dashed UUID formats
    user_id_str = str(user_id).replace('-', '').strip() if '-' in str(user_id) else str(user_id).strip()
    
    # Try to find user by ID (handle both formats)
    user = db.query(User).filter(
        or_(
            User.id == str(user_id),
            User.id == user_id_str
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Support both camelCase and snake_case
    is_active = block_data.isActive if block_data.isActive is not None else block_data.is_active
    
    if is_active is None:
        # Toggle if not provided
        is_active = not user.is_active
    
    user.is_active = is_active
    db.commit()
    
    # Log activity
    try:
        user_uuid = UUID(str(user.id))
    except (ValueError, AttributeError):
        user_uuid = None
    
    if user_uuid:
        log_admin_activity(
            db=db,
            admin_id=admin.id,
            action="user_blocked" if not is_active else "user_unblocked",
            entity_type="user",
            entity_id=user_uuid,
            details={
                "isActive": is_active,
                "reason": block_data.reason
            },
            request=request
        )
    
    return ResponseModel(
        success=True,
        message=f"User {'blocked' if not is_active else 'unblocked'} successfully"
    )


@router.post("/{user_id}/reset-password", response_model=ResponseModel)
async def reset_user_password(
    user_id: str,  # Accept as string to handle both UUID formats
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Reset user password - sends password reset email"""
    # Handle both dashed and non-dashed UUID formats
    user_id_str = str(user_id).replace('-', '').strip() if '-' in str(user_id) else str(user_id).strip()
    
    # Try to find user by ID (handle both formats)
    user = db.query(User).filter(
        or_(
            User.id == str(user_id),
            User.id == user_id_str
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    # In production, store this token in database with expiration
    
    # Send password reset email
    email_sent = send_password_reset_email(user.email, reset_token)
    
    # Log activity
    try:
        user_uuid = UUID(str(user.id))
    except (ValueError, AttributeError):
        user_uuid = None
    
    if user_uuid:
        log_admin_activity(
            db=db,
            admin_id=admin.id,
            action="user_password_reset",
            entity_type="user",
            entity_id=user_uuid,
            details={
                "email": user.email,
                "email_sent": email_sent
            },
            request=request
        )
    
    return ResponseModel(
        success=True,
        message="Password reset email sent successfully"
    )
