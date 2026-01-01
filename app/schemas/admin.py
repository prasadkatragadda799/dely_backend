from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from app.models.admin import AdminRole


# Admin Authentication Schemas
class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminRefreshToken(BaseModel):
    refreshToken: str


class AdminResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: AdminRole
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminTokenResponse(BaseModel):
    token: str
    refreshToken: str
    admin: AdminResponse


# Admin Management Schemas
class AdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    role: AdminRole = AdminRole.SUPPORT


class AdminUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[AdminRole] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


# Activity Log Schema
class AdminActivityLogResponse(BaseModel):
    id: UUID
    admin_id: Optional[UUID] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

