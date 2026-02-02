from pydantic import BaseModel, EmailStr, Field, AliasChoices, model_validator
from typing import Optional, Dict, Any, Union
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
    # NOTE:
    # - Keep this schema permissive to avoid FastAPI 422 for partial updates.
    # - Validation rules (length/format) are enforced in the endpoint logic (400),
    #   so we avoid strict min/max constraints here which commonly break mobile UIs
    #   that send "" for optional fields.

    # Common fields (support snake_case + camelCase input where the app differs)
    name: Optional[str] = Field(default=None, validation_alias=AliasChoices("name", "full_name", "fullName"))

    phone: Optional[str] = Field(default=None, validation_alias=AliasChoices("phone", "phoneNumber", "phone_number"))
    phone_number: Optional[str] = None  # legacy / alternative access (used by some endpoints)

    business_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_name", "businessName")
    )
    business_type: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_type", "businessType")
    )  # Retail, Wholesale, Distributor

    gst_number: Optional[str] = Field(default=None, validation_alias=AliasChoices("gst_number", "gstNumber"))

    fssai_number: Optional[str] = Field(default=None, validation_alias=AliasChoices("fssai_number", "fssaiNumber"))
    fssaiNumber: Optional[str] = None  # legacy / alternative access (used by some endpoints)

    # Legacy field (kept optional for old users)
    pan_number: Optional[str] = Field(default=None, validation_alias=AliasChoices("pan_number", "panNumber"))

    # Business address fields (stored into address JSON by the endpoint)
    business_address: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_address", "businessAddress")
    )
    business_city: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_city", "businessCity")
    )
    business_state: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_state", "businessState")
    )
    business_pincode: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("business_pincode", "businessPincode")
    )

    # User location fields (for activity tracking)
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = Field(default=None, validation_alias=AliasChoices("pincode", "pin_code", "pinCode"))

    # Legacy support: some clients send `address` as a string. Accept both.
    address: Optional[Union[Dict[str, Any], str]] = None

    # Optional GPS fields (some clients send these on profile save)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @model_validator(mode="after")
    def _normalize_update_payload(self):
        """
        Normalize common mobile-app payload quirks:
        - Treat empty strings as None for optional string fields.
        - If `address` is a string, treat it as `business_address` (and clear `address`)
          so the endpoint can store it into the address JSON dict consistently.
        - Coerce numeric pincodes to strings.
        """
        def _clean(v):
            if isinstance(v, str):
                s = v.strip()
                return s if s != "" else None
            return v

        for field_name in [
            "name",
            "phone",
            "phone_number",
            "business_name",
            "business_type",
            "gst_number",
            "fssai_number",
            "fssaiNumber",
            "pan_number",
            "business_address",
            "business_city",
            "business_state",
            "business_pincode",
            "city",
            "state",
            "pincode",
        ]:
            setattr(self, field_name, _clean(getattr(self, field_name)))

        # Keep backward-compat: if phone_number is provided but phone isn't, copy it over.
        if self.phone is None and self.phone_number is not None:
            self.phone = self.phone_number

        # Keep backward-compat: if fssaiNumber is provided but fssai_number isn't, copy it over.
        if self.fssai_number is None and self.fssaiNumber is not None:
            self.fssai_number = self.fssaiNumber

        # If address is a plain string, treat it as business_address
        if isinstance(self.address, str):
            addr = _clean(self.address)
            if addr and self.business_address is None:
                self.business_address = addr
            self.address = None

        # If pincodes were provided as numbers, coerce to strings
        for p_field in ["pincode", "business_pincode"]:
            v = getattr(self, p_field)
            if v is not None and not isinstance(v, str):
                setattr(self, p_field, str(v))

        return self


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
    """
    Flexible login schema:
    - Frontend sends a single `email` field that may actually contain email OR phone.
    - Also accepts explicit `phone`, `phoneNumber`, `phone_number`, or `identifier`.
    """

    # Raw fields from client
    email: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("email", "username"),
    )
    phone: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("phone", "phoneNumber", "phone_number"),
    )
    identifier: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("identifier", "login", "user"),
    )
    password: str = Field(
        ...,
        validation_alias=AliasChoices("password", "pass"),
    )

    @model_validator(mode="after")
    def _normalize_identifier(self):
        """
        Normalise login input so that:
        - If `email` looks like a phone and `phone` is empty, treat it as phone.
        - If `identifier` is provided, route it to email or phone based on contents.
        """
        # If frontend sends a phone in `email` (common "emailOrPhone" pattern)
        if self.email and not self.phone:
            raw = str(self.email).strip()
            if raw and raw.lstrip("+").isdigit() and "@" not in raw:
                # Treat this as phone login
                self.phone = raw
                self.email = None

        # If we still have neither, try identifier
        if (not self.email or str(self.email).strip() == "") and (not self.phone or str(self.phone).strip() == ""):
            if self.identifier and str(self.identifier).strip():
                raw = str(self.identifier).strip()
                if raw.lstrip("+").isdigit() and "@" not in raw:
                    self.phone = raw
                else:
                    self.email = raw

        if (not self.email or str(self.email).strip() == "") and (not self.phone or str(self.phone).strip() == ""):
            raise ValueError("Either email/username or phone/phoneNumber must be provided")

        return self


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserResponse

