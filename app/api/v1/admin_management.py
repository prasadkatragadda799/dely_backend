"""
Admin User Management Endpoints
For managing admin users (CRUD operations)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.settings import AdminUserCreate, AdminUserUpdate, AdminUserResponse
from app.models.admin import Admin, AdminRole
from app.api.admin_deps import require_admin_or_super_admin, require_super_admin, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.security import get_password_hash

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def get_all_admins(
    admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all admin users.
    Requires admin or super_admin role.
    """
    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    
    admin_list = []
    for a in admins:
        admin_data = {
            "id": str(a.id),
            "name": a.name,
            "email": a.email,
            "role": a.role.value,
            "status": "active" if a.is_active else "inactive",
            "lastLogin": a.last_login.isoformat() if a.last_login else None,
            "createdAt": a.created_at.isoformat() if a.created_at else None,
            "updatedAt": a.updated_at.isoformat() if a.updated_at else None
        }
        admin_list.append(admin_data)
    
    return ResponseModel(
        success=True,
        data=admin_list,
        message="Admin users retrieved successfully"
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_admin(
    admin_data: AdminUserCreate,
    request: Request,
    current_admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new admin user.
    Requires admin or super_admin role.
    Only super_admin can create other super_admin users.
    """
    # Check if email already exists
    existing_admin = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Only super_admin can create super_admin users
    if admin_data.role == "super_admin" and current_admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create super admin users"
        )
    
    # Hash password
    password_hash = get_password_hash(admin_data.password)
    
    # Create admin user
    new_admin = Admin(
        email=admin_data.email,
        name=admin_data.name,
        password_hash=password_hash,
        role=AdminRole(admin_data.role),
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=current_admin.id,
        action="admin_created",
        entity_type="admin",
        entity_id=new_admin.id,
        details={
            "admin_name": new_admin.name,
            "admin_email": new_admin.email,
            "admin_role": new_admin.role.value
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": str(new_admin.id),
            "name": new_admin.name,
            "email": new_admin.email,
            "role": new_admin.role.value,
            "status": "active",
            "createdAt": new_admin.created_at.isoformat() if new_admin.created_at else None
        },
        message="Admin user created successfully"
    )


@router.put("/{admin_id}", response_model=ResponseModel)
async def update_admin(
    admin_id: str,
    admin_data: AdminUserUpdate,
    request: Request,
    current_admin: Admin = Depends(require_admin_or_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update an admin user.
    Requires admin or super_admin role.
    Only super_admin can modify super_admin users.
    Users cannot modify themselves (except password).
    """
    try:
        admin_uuid = UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid admin ID format")
    
    # Get admin to update
    target_admin = db.query(Admin).filter(Admin.id == admin_uuid).first()
    if not target_admin:
        raise HTTPException(status_code=404, detail="Admin user not found")
    
    # Only super_admin can modify super_admin users
    if target_admin.role == AdminRole.SUPER_ADMIN and current_admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can modify super admin users"
        )
    
    # Prevent self-modification (except password)
    if str(target_admin.id) == str(current_admin.id):
        if any([admin_data.name, admin_data.email, admin_data.role, admin_data.status, admin_data.is_active]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot modify your own account details. You can only change your password."
            )
    
    # Update fields
    if admin_data.name is not None:
        target_admin.name = admin_data.name
    
    if admin_data.email is not None:
        # Check if email already exists
        existing_admin = db.query(Admin).filter(
            Admin.email == admin_data.email,
            Admin.id != admin_uuid
        ).first()
        if existing_admin:
            raise HTTPException(status_code=400, detail="Email already in use")
        target_admin.email = admin_data.email
    
    if admin_data.password is not None:
        target_admin.password_hash = get_password_hash(admin_data.password)
    
    if admin_data.role is not None:
        # Only super_admin can change roles to/from super_admin
        if (admin_data.role == "super_admin" or target_admin.role == AdminRole.SUPER_ADMIN) and current_admin.role != AdminRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can change super admin roles"
            )
        target_admin.role = AdminRole(admin_data.role)
    
    # Handle status or is_active
    if admin_data.status is not None:
        target_admin.is_active = admin_data.status == "active"
    elif admin_data.is_active is not None:
        target_admin.is_active = admin_data.is_active
    
    db.commit()
    db.refresh(target_admin)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=current_admin.id,
        action="admin_updated",
        entity_type="admin",
        entity_id=target_admin.id,
        details={
            "admin_name": target_admin.name,
            "admin_email": target_admin.email
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": str(target_admin.id),
            "name": target_admin.name,
            "email": target_admin.email,
            "role": target_admin.role.value,
            "status": "active" if target_admin.is_active else "inactive",
            "updatedAt": target_admin.updated_at.isoformat() if target_admin.updated_at else None
        },
        message="Admin user updated successfully"
    )


@router.delete("/{admin_id}", response_model=ResponseModel)
async def delete_admin(
    admin_id: str,
    request: Request,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete an admin user (soft delete - sets is_active to false).
    Requires super_admin role.
    Cannot delete yourself.
    Cannot delete the last super_admin.
    """
    try:
        admin_uuid = UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid admin ID format")
    
    # Get admin to delete
    target_admin = db.query(Admin).filter(Admin.id == admin_uuid).first()
    if not target_admin:
        raise HTTPException(status_code=404, detail="Admin user not found")
    
    # Prevent self-deletion
    if str(target_admin.id) == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete your own account"
        )
    
    # Prevent deletion of last super_admin
    if target_admin.role == AdminRole.SUPER_ADMIN:
        super_admin_count = db.query(func.count(Admin.id)).filter(
            Admin.role == AdminRole.SUPER_ADMIN,
            Admin.is_active == True
        ).scalar()
        
        if super_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete the last super admin user"
            )
    
    # Soft delete
    target_admin.is_active = False
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=current_admin.id,
        action="admin_deleted",
        entity_type="admin",
        entity_id=target_admin.id,
        details={
            "admin_name": target_admin.name,
            "admin_email": target_admin.email
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Admin user deleted successfully"
    )
