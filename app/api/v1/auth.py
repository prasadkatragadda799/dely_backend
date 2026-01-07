from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, ChangePassword
from app.schemas.common import ResponseModel
from app.services.auth_service import register_user, authenticate_user, create_tokens
from app.models.user import User
from app.utils.security import verify_password, get_password_hash, decode_token, create_access_token
from app.utils.email import send_password_reset_email
from app.api.deps import get_current_user
from datetime import timedelta
from app.config import settings
import secrets


class RefreshTokenRequest(BaseModel):
    refreshToken: str

router = APIRouter()


@router.post("/register", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with kyc_status = 'not_verified'"""
    try:
        user = register_user(db, user_data)
        tokens = create_tokens(user)
        
        # Get KYC status as string with all variations
        kyc_status = user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status)
        is_kyc_verified = kyc_status == "verified"
        
        # Format user data with all field variations
        user_data_response = {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "business_name": user.business_name,
            "kyc_status": kyc_status,
            "kycStatus": kyc_status,  # camelCase alternative
            "is_kyc_verified": is_kyc_verified,  # Boolean alternative
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
        return ResponseModel(
            success=True,
            data={
                "user": user_data_response,
                "token": tokens["token"],
                "refresh_token": tokens["refresh_token"]
            },
            message="Registration successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/login", response_model=ResponseModel)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user with email OR phone"""
    try:
        user = authenticate_user(
            db, 
            email=credentials.email, 
            phone=credentials.phone,
            password=credentials.password
        )
        tokens = create_tokens(user)
        
        # Get KYC status as string with all variations
        kyc_status = user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status)
        is_kyc_verified = kyc_status == "verified"
        
        # Format user data with all field variations
        user_data_response = {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "business_name": user.business_name,
            "kyc_status": kyc_status,
            "kycStatus": kyc_status,  # camelCase alternative
            "is_kyc_verified": is_kyc_verified,  # Boolean alternative
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
        return ResponseModel(
            success=True,
            data={
                "user": user_data_response,
                "token": tokens["token"],
                "refresh_token": tokens["refresh_token"]
            },
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/forgot-password", response_model=ResponseModel)
def forgot_password(email: str, db: Session = Depends(get_db)):
    """Send password reset email"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return ResponseModel(
            success=True,
            message="If the email exists, a password reset link has been sent"
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    # In production, store this token in database with expiration
    
    # Send email
    send_password_reset_email(email, reset_token)
    
    return ResponseModel(
        success=True,
        message="Password reset link has been sent to your email"
    )


@router.post("/reset-password", response_model=ResponseModel)
def reset_password(token: str, new_password: str, confirm_password: str, db: Session = Depends(get_db)):
    """Reset password using token"""
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # In production, verify token from database
    # For now, decode token to get user info
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Password reset successfully"
    )


@router.post("/refresh-token", response_model=ResponseModel)
def refresh_token(
    request_data: RefreshTokenRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    payload = decode_token(request_data.refreshToken)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    tokens = create_tokens(user)
    
    return ResponseModel(
        success=True,
        data={
            "token": tokens["token"],
            "refresh_token": tokens["refresh_token"]
        },
        message="Token refreshed successfully"
    )


@router.post("/logout", response_model=ResponseModel)
def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)"""
    # In production, you might want to blacklist tokens
    return ResponseModel(
        success=True,
        message="Logged out successfully"
    )

