from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from datetime import timedelta, datetime
from app.config import settings
import re


def register_user(db: Session, user_data: UserCreate) -> User:
    """Register a new user (phone-based, no email required)"""
    # Check if phone already exists
    existing_phone_user = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_phone_user:
        if existing_phone_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        # Unverified account — delete it so the user can re-register
        db.delete(existing_phone_user)
        db.commit()

    # Validate password match
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Create address dict
    address = None
    if user_data.city and user_data.state and user_data.pincode:
        address = {
            "city": user_data.city,
            "state": user_data.state,
            "pincode": user_data.pincode,
            "address": user_data.address or {}
        }

    from app.models.user import KYCStatus

    fssai_digits = None
    raw_fssai = getattr(user_data, "fssai_number", None)
    if raw_fssai:
        digits = re.sub(r"\D", "", str(raw_fssai).strip())
        if len(digits) == 14:
            fssai_digits = digits

    user = User(
        name=user_data.name,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password),
        business_name=user_data.business_name,
        gst_number=user_data.gst_number,
        gst_certificate=user_data.gst_certificate,
        fssai_license=user_data.fssai_license,
        udyam_registration=user_data.udyam_registration,
        trade_certificate=user_data.trade_certificate,
        fssai_number=fssai_digits,
        address=address,
        city=user_data.city,
        state=user_data.state,
        pincode=user_data.pincode,
        kyc_status=KYCStatus.NOT_VERIFIED,
        is_active=False,
        last_active_at=datetime.utcnow()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, phone: str = None, password: str = None) -> User:
    """Authenticate user by phone number"""
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required"
        )

    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )

    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first."
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify OTP first."
        )

    user.last_active_at = datetime.utcnow()
    db.commit()

    return user


def create_tokens(user: User) -> dict:
    """Create access and refresh tokens for user"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )

    return {
        "token": access_token,
        "refresh_token": refresh_token
    }
