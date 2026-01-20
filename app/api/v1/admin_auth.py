"""
Admin Authentication Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID
from app.database import get_db
from app.schemas.admin import AdminLogin, AdminRefreshToken, AdminResponse, AdminTokenResponse
from app.schemas.common import ResponseModel
from app.models.admin import Admin
from app.utils.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.api.admin_deps import get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=ResponseModel)
async def admin_login(
    credentials: AdminLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin login"""
    admin = db.query(Admin).filter(Admin.email == credentials.email).first()
    
    if not admin or not verify_password(credentials.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    token_data = {
        "adminId": str(admin.id),
        "email": admin.email,
        "role": admin.role.value
    }
    token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="admin_login",
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "token": token,
            "refreshToken": refresh_token,
            "admin": AdminResponse.model_validate(admin)
        },
        message="Login successful"
    )


@router.post("/refresh-token", response_model=ResponseModel)
async def refresh_token(
    token_data: AdminRefreshToken,
    db: Session = Depends(get_db)
):
    """Refresh admin access token"""
    payload = decode_token(token_data.refreshToken)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    admin_id = payload.get("adminId") or payload.get("sub")
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Convert string UUID to UUID object if needed
    try:
        if isinstance(admin_id, str):
            admin_id = UUID(admin_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new tokens
    token_data_new = {
        "adminId": str(admin.id),
        "email": admin.email,
        "role": admin.role.value
    }
    token = create_access_token(token_data_new)
    refresh_token_new = create_refresh_token(token_data_new)
    
    return ResponseModel(
        success=True,
        data={
            "token": token,
            "refreshToken": refresh_token_new
        },
        message="Token refreshed successfully"
    )


@router.get("/me", response_model=ResponseModel)
async def get_current_admin_info(
    admin: Admin = Depends(get_current_active_admin)
):
    """Get current admin information"""
    return ResponseModel(
        success=True,
        data=AdminResponse.model_validate(admin),
        message="Admin information retrieved successfully"
    )


@router.put("/change-password", response_model=ResponseModel)
async def change_admin_password(
    request: Request,
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Change current admin/seller password"""
    from pydantic import BaseModel
    
    class PasswordChange(BaseModel):
        currentPassword: str
        newPassword: str
    
    # Parse request body
    body = await request.json()
    password_data = PasswordChange(**body)
    
    # Verify current password
    if not verify_password(password_data.currentPassword, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(password_data.newPassword) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Update password
    admin.password_hash = get_password_hash(password_data.newPassword)
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Password updated successfully"
    )


@router.post("/logout", response_model=ResponseModel)
async def admin_logout(
    request: Request,
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Admin logout"""
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="admin_logout",
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Logout successful"
    )

