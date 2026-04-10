from typing import Optional

import json

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Form, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, model_validator
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
import logging
import threading
import time


class RefreshTokenRequest(BaseModel):
    refreshToken: str

router = APIRouter()

logger = logging.getLogger(__name__)

_otp_rate_lock = threading.Lock()
_otp_send_rate: dict[str, list[float]] = {}
_otp_verify_rate: dict[str, list[float]] = {}
OTP_SEND_LIMIT = 5
OTP_SEND_WINDOW_SEC = 60
OTP_VERIFY_LIMIT = 8
OTP_VERIFY_WINDOW_SEC = 10 * 60


def _normalize_phone_digits(phone_raw: str) -> str:
    return "".join(ch for ch in str(phone_raw or "").strip() if ch.isdigit())


def _is_playstore_test_phone(phone_raw: str) -> bool:
    if not settings.PLAYSTORE_TEST_OTP_ENABLED:
        return False
    normalized = _normalize_phone_digits(phone_raw)
    base = _normalize_phone_digits(settings.PLAYSTORE_TEST_PHONE)
    if not base:
        return False
    with_cc = f"91{base}"
    return normalized in {base, with_cc}


def _mask_phone(phone_raw: str) -> str:
    n = _normalize_phone_digits(phone_raw)
    if len(n) <= 4:
        return "****"
    return f"{'*' * (len(n) - 4)}{n[-4:]}"


def _check_rate_limit(bucket: dict[str, list[float]], key: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    cutoff = now - window_seconds
    with _otp_rate_lock:
        entries = [t for t in bucket.get(key, []) if t >= cutoff]
        if len(entries) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )
        entries.append(now)
        bucket[key] = entries


def _finalize_registration_otp(db: Session, user: User, phone_raw: str) -> ResponseModel:
    """Send 2Factor OTP after user row exists; delete user if OTP cannot be sent."""
    if _is_playstore_test_phone(phone_raw):
        logger.info("[auth.register] test OTP bypass active phone=%s", _mask_phone(phone_raw))
        return ResponseModel(
            success=True,
            data={
                "request_id": settings.PLAYSTORE_TEST_REQUEST_ID,
                "user_id": str(user.id),
                "phone": user.phone,
            },
            message="Registration successful. OTP sent.",
        )

    if not settings.TWO_FACTOR_API_KEY:
        logger.error("[auth.register] TWO_FACTOR_API_KEY missing")
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TWO_FACTOR_API_KEY is not configured",
        )

    phone = (phone_raw or "").strip()
    normalized = _normalize_phone_digits(phone)
    if len(normalized) < 10:
        logger.warning("[auth.register] invalid phone=%s", _mask_phone(phone))
        db.delete(user)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

    url = f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/{normalized}/AUTOGEN"
    logger.info("[auth.register] sending OTP phone=%s", _mask_phone(normalized))
    resp = requests.get(url, timeout=10)
    data = resp.json() if resp.content else {}

    if (data or {}).get("Status") != "Success" or not (data or {}).get("Details"):
        logger.warning("[auth.register] OTP send failed phone=%s", _mask_phone(normalized))
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send OTP",
        )

    request_id = str(data["Details"])
    logger.info("[auth.register] OTP sent phone=%s", _mask_phone(normalized))

    return ResponseModel(
        success=True,
        data={
            "request_id": request_id,
            "user_id": str(user.id),
            "phone": user.phone,
        },
        message="Registration successful. OTP sent.",
    )


async def _save_registration_upload(
    file: Optional[UploadFile],
    request: Request,
    user_id: str,
) -> Optional[str]:
    """Persist one registration image under uploads/user_registration/{user_id}/."""
    if file is None:
        return None
    from app.api.v1.admin_upload import validate_image_file, write_image_upload

    file_ext, _ = validate_image_file(file)
    content = await file.read()
    if not content:
        return None
    return write_image_upload(content, file_ext, "user_registration", user_id, request)


@router.post("/register", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (JSON body), then send OTP for verification."""
    try:
        user = register_user(db, user_data)
        return _finalize_registration_otp(db, user, user_data.phone)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[auth.register] unhandled registration error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user. Please try again.",
        )


@router.post("/register/multipart", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def register_multipart(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    business_name: str = Form(...),
    gst_number: Optional[str] = Form(None),
    fssai_number: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    pincode: Optional[str] = Form(None),
    address_json: Optional[str] = Form(None),
    gst_certificate: Optional[UploadFile] = File(None),
    fssai_license: Optional[UploadFile] = File(None),
    udyam_registration: Optional[UploadFile] = File(None),
    trade_certificate: Optional[UploadFile] = File(None),
    shop_photo: Optional[UploadFile] = File(None),
    user_id_document: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Register with certificate images as multipart/form-data.
    Saves files to disk and stores public URLs on the user row (same as product uploads).
    """
    address = None
    if address_json and str(address_json).strip():
        try:
            address = json.loads(address_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid address_json")

    user_data = UserCreate(
        name=name.strip(),
        email=email.strip(),
        phone=phone.strip(),
        business_name=business_name.strip(),
        password=password,
        confirm_password=confirm_password,
        gst_number=(gst_number or "").strip() or None,
        fssai_number=(fssai_number or "").strip() or None,
        gst_certificate=None,
        fssai_license=None,
        udyam_registration=None,
        trade_certificate=None,
        city=(city or "").strip() or None,
        state=(state or "").strip() or None,
        pincode=(pincode or "").strip() or None,
        address=address,
    )

    try:
        user = register_user(db, user_data)
        uid = str(user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[auth.register.multipart] registration failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user. Please try again.",
        )

    try:
        if gst_certificate:
            url = await _save_registration_upload(gst_certificate, request, uid)
            if url:
                user.gst_certificate = url
        if fssai_license:
            url = await _save_registration_upload(fssai_license, request, uid)
            if url:
                user.fssai_license = url
        if udyam_registration:
            url = await _save_registration_upload(udyam_registration, request, uid)
            if url:
                user.udyam_registration = url
        if trade_certificate:
            url = await _save_registration_upload(trade_certificate, request, uid)
            if url:
                user.trade_certificate = url
        if shop_photo:
            url = await _save_registration_upload(shop_photo, request, uid)
            if url:
                user.shop_photo_url = url
        if user_id_document:
            url = await _save_registration_upload(user_id_document, request, uid)
            if url:
                user.user_id_document_url = url
        db.add(user)
        db.commit()
        db.refresh(user)
    except HTTPException:
        u = db.query(User).filter(User.id == uid).first()
        if u:
            db.delete(u)
            db.commit()
        raise
    except Exception as e:
        u = db.query(User).filter(User.id == uid).first()
        if u:
            db.delete(u)
            db.commit()
        logger.exception("[auth.register.multipart] upload handling failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process registration files. Please try again.",
        )

    try:
        return _finalize_registration_otp(db, user, user_data.phone)
    except HTTPException:
        u = db.query(User).filter(User.id == uid).first()
        if u:
            db.delete(u)
            db.commit()
        raise


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
    except Exception:
        logger.exception("[auth.login] unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
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

    normalized = _normalize_phone_digits(phone)
    if len(normalized) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
    _check_rate_limit(_otp_send_rate, f"send:{normalized}", OTP_SEND_LIMIT, OTP_SEND_WINDOW_SEC)

    if _is_playstore_test_phone(phone):
        logger.info("[auth.send_otp] test OTP bypass active phone=%s", _mask_phone(phone))
        return ResponseModel(
            success=True,
            data={"request_id": settings.PLAYSTORE_TEST_REQUEST_ID},
            message="OTP sent",
        )

    if not settings.TWO_FACTOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TWO_FACTOR_API_KEY is not configured",
        )

    url = f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/{normalized}/AUTOGEN"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json() if resp.content else {}
    except Exception:
        logger.exception("[auth.send_otp] provider request failed")
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
    # Client may send either `requestId` (camelCase) or `request_id` (snake_case).
    # Normalize both into `request_id` before validation.
    request_id: Optional[str] = None
    otp: str

    @model_validator(mode="before")
    @classmethod
    def _coerce_request_id_aliases(cls, data):
        if isinstance(data, dict):
            if "request_id" not in data and "requestId" in data:
                data = {**data, "request_id": data.get("requestId")}
        return data


@router.post("/verify-otp", response_model=ResponseModel)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Verify OTP via 2Factor, then issue JWT tokens for the user matching the phone.
    """
    phone_raw = (payload.phone or "").strip()
    request_id = (payload.request_id or "").strip()
    otp = (payload.otp or "").strip()

    if not phone_raw or not request_id or not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone, request_id, and otp are required",
        )

    normalized = _normalize_phone_digits(phone_raw)
    if len(normalized) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
    _check_rate_limit(_otp_verify_rate, f"verify:{normalized}", OTP_VERIFY_LIMIT, OTP_VERIFY_WINDOW_SEC)

    is_playstore_test = _is_playstore_test_phone(phone_raw)
    if is_playstore_test:
        if request_id != settings.PLAYSTORE_TEST_REQUEST_ID:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP session")
        if otp != settings.PLAYSTORE_TEST_OTP:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")
    else:
        if not settings.TWO_FACTOR_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TWO_FACTOR_API_KEY is not configured",
            )
        verify_url = (
            f"https://2factor.in/API/V1/{settings.TWO_FACTOR_API_KEY}/SMS/VERIFY/{request_id}/{otp}"
        )
        try:
            resp = requests.get(verify_url, timeout=10)
            data = resp.json() if resp.content else {}
        except Exception:
            logger.exception("[auth.verify_otp] provider verify failed")
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

