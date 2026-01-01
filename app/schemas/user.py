from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    business_name: str
    gst_number: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    confirm_password: str
    address: Optional[Dict[str, Any]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str
    business_name: str
    gst_number: Optional[str]
    address: Optional[Dict[str, Any]]
    kyc_status: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserResponse

