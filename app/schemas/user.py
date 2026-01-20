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
    name: Optional[str] = Field(None, min_length=2)
    phone: Optional[str] = None
    phone_number: Optional[str] = None  # Alternative field name
    business_name: Optional[str] = Field(None, min_length=2)
    business_type: Optional[str] = None  # Retail, Wholesale, Distributor
    gst_number: Optional[str] = Field(None, max_length=15, min_length=15)
    pan_number: Optional[str] = Field(None, max_length=10, min_length=10)
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_pincode: Optional[str] = Field(None, max_length=6, min_length=6)
    # User location fields (for activity tracking)
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = Field(None, max_length=6, min_length=6)
    address: Optional[Dict[str, Any]] = None  # Legacy support


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
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserResponse

