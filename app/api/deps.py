from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.security import verify_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


async def require_kyc_verified(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require KYC verification for accessing products/companies"""
    from fastapi.responses import JSONResponse
    from app.models.user import KYCStatus
    
    kyc_status = current_user.kyc_status
    kyc_status_value = kyc_status.value if hasattr(kyc_status, 'value') else str(kyc_status)
    
    if kyc_status_value != "verified":
        # Map status to response format
        if kyc_status_value == "pending":
            status_for_response = "pending"
        else:
            status_for_response = "not_verified"
        
        # Return proper JSON response format
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "KYC verification required. Please complete your business verification to access products.",
                "error": "KYC_NOT_VERIFIED",
                "kyc_status": status_for_response
            }
        )
    
    return current_user

