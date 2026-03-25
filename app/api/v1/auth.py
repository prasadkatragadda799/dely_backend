from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, ChangePassword
from app.schemas.common import ResponseModel
from app.services.auth_service import register_user, authenticate_user, create_tokens
from app.models.user import User
from app.utils.security import verify_password, get_password_hash, decode_token, create_access_token
from app.utils.email import send_password_reset_email
from app.api.deps import get_current_user
from datetime import timedelta, datetime
from app.config import settings
import secrets
import requests


class RefreshTokenRequest(BaseModel):
    refreshToken: str

router = APIRouter()


@router.post("/register", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user, then send OTP for verification."""
    try:
        user = register_user(db, user_data)
        
        # Send OTP immediately after creating the user.
        # NOTE: OTP verification is required before the user can login.
        if not settings.TWO_FACTOR_API_KEY:
            # Avoid leaving an unusable user record behind.
            db.delete(user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TWO_FACTOR_API_KEY is not configured",
            )

        phone = (user_data.phone or "").strip()
        normalized = "".join(ch for ch in phone if ch.isdigit())
        if len(normalized) < 10:
            db.delete(user)
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

        url = f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/{normalized}/AUTOGEN"
        resp = requests.get(url, timeout=10)
        data = resp.json() if resp.content else {}

        if (data or {}).get("Status") != "Success" or not (data or {}).get("Details"):
            db.delete(user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to send OTP",
            )

        request_id = str(data["Details"])

        return ResponseModel(
            success=True,
            data={
                "request_id": request_id,
                "user_id": str(user.id),
                "phone": user.phone,
            },
            message="Registration successful. OTP sent.",
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


class SendOtpRequest(BaseModel):
    phone: str


class SendOtpResponse(BaseModel):
    request_id: str


@router.post("/send-otp", response_model=ResponseModel)
def send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    """
    Send OTP via 2Factor to the given mobile number.
    Returns a request_id (session id) used to verify OTP.
    """
    phone = (payload.phone or "").strip()
    if not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone is required")

    if not settings.TWO_FACTOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TWO_FACTOR_API_KEY is not configured",
        )

    # Keep it simple: allow digits only (client should send normalized number).
    normalized = "".join(ch for ch in phone if ch.isdigit())
    if len(normalized) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

    url = f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/{normalized}/AUTOGEN"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json() if resp.content else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send OTP",
        )

    if (data or {}).get("Status") != "Success" or not (data or {}).get("Details"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send OTP",
        )

    request_id = str(data["Details"])
    return ResponseModel(
        success=True,
        data={"request_id": request_id},
        message="OTP sent",
    )


# Backwards-compatible aliases for clients that use different path styles.
@router.post("/send_otp", response_model=ResponseModel)
def send_otp_alias(payload: SendOtpRequest, db: Session = Depends(get_db)):
    return send_otp(payload, db)


@router.post("/sendOtp", response_model=ResponseModel)
def send_otp_camel_alias(payload: SendOtpRequest, db: Session = Depends(get_db)):
    return send_otp(payload, db)


@router.post("/sendotp", response_model=ResponseModel)
def send_otp_no_dash_alias(payload: SendOtpRequest, db: Session = Depends(get_db)):
    return send_otp(payload, db)


class VerifyOtpRequest(BaseModel):
    phone: str
    requestId: str = Field(validation_alias="request_id")
    otp: str


@router.post("/verify-otp", response_model=ResponseModel)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Verify OTP via 2Factor, then issue JWT tokens for the user matching the phone.
    """
    phone_raw = (payload.phone or "").strip()
    request_id = (payload.requestId or "").strip()
    otp = (payload.otp or "").strip()

    if not phone_raw or not request_id or not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone, requestId, and otp are required",
        )

    if not settings.TWO_FACTOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TWO_FACTOR_API_KEY is not configured",
        )

    normalized = "".join(ch for ch in phone_raw if ch.isdigit())
    if len(normalized) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

    verify_url = (
        f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/VERIFY/{request_id}/{otp}"
    )
    try:
        resp = requests.get(verify_url, timeout=10)
        data = resp.json() if resp.content else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify OTP",
        )

    if (data or {}).get("Status") != "Success":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    # OTP verified: login user by phone
    # Phones in DB may include '+'/'spaces; try both raw and normalized.
    user = db.query(User).filter(User.phone.in_([phone_raw, normalized])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Activate user after successful OTP verification.
    if not user.is_active:
        user.is_active = True
        user.last_active_at = datetime.utcnow()
        db.commit()

    tokens = create_tokens(user)

    kyc_status = user.kyc_status.value if hasattr(user.kyc_status, "value") else str(user.kyc_status)
    is_kyc_verified = kyc_status == "verified"
    user_data_response = {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "business_name": user.business_name,
        "kyc_status": kyc_status,
        "kycStatus": kyc_status,
        "is_kyc_verified": is_kyc_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    return ResponseModel(
        success=True,
        data={
            "user": user_data_response,
            "token": tokens["token"],
            "refresh_token": tokens["refresh_token"],
        },
        message="OTP verified",
    )


@router.post("/verify_otp", response_model=ResponseModel)
def verify_otp_alias(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return verify_otp(payload, db)


@router.post("/verifyOtp", response_model=ResponseModel)
def verify_otp_camel_alias(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return verify_otp(payload, db)


@router.post("/verifyotp", response_model=ResponseModel)
def verify_otp_no_dash_alias(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return verify_otp(payload, db)

