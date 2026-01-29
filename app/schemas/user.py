from pydantic import BaseModel, EmailStr, Field, AliasChoices, model_validator
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
    fssai_number: Optional[str] = Field(None, max_length=14, min_length=14)
    fssaiNumber: Optional[str] = Field(None, max_length=14, min_length=14)  # camelCase alternative
    # Legacy field (keep optional during transition)
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
    # Accept common client field-name variants.
    email: Optional[EmailStr] = Field(
        default=None,
        validation_alias=AliasChoices("email", "username"),
    )
    phone: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("phone", "phoneNumber", "phone_number"),
    )
    # Some clients send a single identifier field; backend will treat it as phone if it looks numeric,
    # otherwise as email.
    identifier: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("identifier", "login", "user"),
    )
    password: str = Field(
        ...,
        validation_alias=AliasChoices("password", "pass"),
    )

    @model_validator(mode="after")
    def _ensure_identifier_present(self):
        if (self.email is None or str(self.email).strip() == "") and (self.phone is None or str(self.phone).strip() == ""):
            if self.identifier and str(self.identifier).strip():
                raw = str(self.identifier).strip()
                # If it contains only digits/+ prefix, treat as phone; else treat as email.
                if raw.lstrip("+").isdigit():
                    self.phone = raw
                else:
                    # Let EmailStr validation run on next parse; here we just set the string.
                    self.email = raw  # type: ignore[assignment]
        if (self.email is None or str(self.email).strip() == "") and (self.phone is None or str(self.phone).strip() == ""):
            raise ValueError("Either email/username, phone/phoneNumber, or identifier must be provided")
        return self


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserResponse

