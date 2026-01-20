"""
Admin Dependencies for Authentication and Authorization
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.utils.security import decode_token
from app.models.admin import Admin, AdminRole
from app.utils.admin_activity import log_admin_activity

# Use HTTPBearer for better Swagger UI compatibility
http_bearer = HTTPBearer(auto_error=False)
# OAuth2PasswordBearer with auto_error=False for fallback
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/admin/auth/login", auto_error=False)


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    token: Optional[str] = Depends(oauth2_scheme_admin),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current authenticated admin"""
    import logging
    logger = logging.getLogger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from multiple sources (try all methods)
    auth_token = None
    
    # Method 1: HTTPBearer (preferred for Swagger UI)
    if credentials and credentials.credentials:
        auth_token = credentials.credentials
        logger.debug(f"Token from HTTPBearer: {auth_token[:20]}...")
    
    # Method 2: OAuth2PasswordBearer
    elif token:
        auth_token = token
        logger.debug(f"Token from OAuth2PasswordBearer: {auth_token[:20]}...")
    
    # Method 3: Direct header extraction (fallback)
    if not auth_token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Extract token from "Bearer <token>" format
            if auth_header.startswith("Bearer "):
                auth_token = auth_header[7:]  # Remove "Bearer " prefix
                logger.debug(f"Token from Authorization header: {auth_token[:20]}...")
            elif auth_header.startswith("bearer "):
                auth_token = auth_header[7:]  # Case insensitive
                logger.debug(f"Token from authorization header (lowercase): {auth_token[:20]}...")
    
    # Debug: Check if token is received
    if not auth_token:
        logger.error(f"No token found. Headers: Authorization={request.headers.get('Authorization', 'NOT FOUND')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided. Please authorize using the 'Authorize' button in Swagger UI and make sure to click 'Authorize' after entering the token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Token received: {auth_token[:20]}...")
    
    payload = decode_token(auth_token)
    if payload is None:
        logger.error("Token decode failed - invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Token payload: {payload}")
    
    admin_id = payload.get("adminId") or payload.get("sub")
    if admin_id is None:
        logger.error(f"Token missing admin ID. Payload keys: {payload.keys()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing admin ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Admin ID from token: {admin_id} (type: {type(admin_id)})")
    
    # Convert string UUID to UUID object if needed
    try:
        if isinstance(admin_id, str):
            admin_id = UUID(admin_id)
            logger.debug(f"Converted admin_id to UUID: {admin_id}")
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid admin ID format: {admin_id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid admin ID format: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if admin is None:
        logger.error(f"Admin not found in database with ID: {admin_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Admin not found with ID: {admin_id}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Admin found: {admin.email}, active: {admin.is_active}")
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    return admin


async def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Get current active admin"""
    if not current_admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    return current_admin


def require_role(allowed_roles: List[AdminRole]):
    """
    Dependency factory for role-based access control
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(admin: Admin = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))):
            ...
    """
    async def role_checker(
        current_admin: Admin = Depends(get_current_active_admin)
    ) -> Admin:
        if current_admin.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_admin
    
    return role_checker


# Role-specific dependency functions (use with Depends() in endpoints)
async def require_super_admin(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """Require super admin role"""
    if current_admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required."
        )
    return current_admin

async def require_admin_or_super_admin(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """Require admin or super admin role"""
    if current_admin.role not in [AdminRole.SUPER_ADMIN, AdminRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or super admin role required."
        )
    return current_admin

async def require_manager_or_above(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """Require manager, admin, or super admin role"""
    if current_admin.role not in [AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Manager, admin, or super admin role required."
        )
    return current_admin


async def require_seller_or_above(
    current_admin: Admin = Depends(get_current_active_admin)
) -> Admin:
    """Require seller, manager, admin, or super admin role"""
    if current_admin.role not in [AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MANAGER, AdminRole.SELLER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Seller, manager, admin, or super admin role required."
        )
    return current_admin


def require_seller():
    """Require seller role only"""
    async def seller_checker(
        current_admin: Admin = Depends(get_current_active_admin)
    ) -> Admin:
        if current_admin.role != AdminRole.SELLER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Seller role required."
            )
        return current_admin
    return seller_checker

