from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID


class GSTVerify(BaseModel):
    gst_number: str


class GSTVerifyResponse(BaseModel):
    gst_number: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    status: Optional[str] = None
    registration_date: Optional[str] = None
    business_type: Optional[str] = None
    address: Optional[Dict[str, Any]] = None


class KYCSubmit(BaseModel):
    business_name: Optional[str] = None
    businessName: Optional[str] = None  # camelCase alternative
    gst_number: Optional[str] = None
    gstNumber: Optional[str] = None  # camelCase alternative
    fssai_number: Optional[str] = None
    fssaiNumber: Optional[str] = None  # camelCase alternative
    fssaiLicenseNumber: Optional[str] = None  # extra camelCase alternative
    pan_number: Optional[str] = None
    panNumber: Optional[str] = None  # camelCase alternative
    business_type: Optional[str] = None
    businessType: Optional[str] = None  # camelCase alternative
    address: Optional[Union[str, Dict[str, Any]]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    business_license: Optional[str] = None
    businessLicense: Optional[str] = None  # camelCase alternative
    documents: Optional[Dict[str, Any]] = None
    
    def model_post_init(self, __context):
        """Normalize field names and construct address dict"""
        # Use camelCase if provided, otherwise use snake_case
        self.business_name = self.business_name or self.businessName or ""
        self.gst_number = self.gst_number or self.gstNumber or ""
        self.fssai_number = self.fssai_number or self.fssaiNumber or self.fssaiLicenseNumber or ""
        self.pan_number = self.pan_number or self.panNumber or ""
        self.business_type = self.business_type or self.businessType or "retailer"  # Default to retailer
        self.business_license = self.business_license or self.businessLicense
        
        # Construct address dict from individual fields or use provided address
        if isinstance(self.address, str):
            # If address is a string, create a dict with it
            address_dict = {
                "address": self.address.strip() if self.address else "",
                "city": self.city or "",
                "state": self.state or "",
                "pincode": self.pincode or ""
            }
        elif isinstance(self.address, dict):
            # If address is already a dict, merge with individual fields
            address_dict = {
                "address": self.address.get("address", self.address.get("address_line1", "")),
                "city": self.city or self.address.get("city", ""),
                "state": self.state or self.address.get("state", ""),
                "pincode": self.pincode or self.address.get("pincode", "")
            }
        else:
            # Create from individual fields
            address_dict = {
                "address": "",
                "city": self.city or "",
                "state": self.state or "",
                "pincode": self.pincode or ""
            }
        
        self.address = address_dict
        
        # Add business license to documents if provided
        if self.business_license and not self.documents:
            self.documents = {"business_license": self.business_license}
        elif self.business_license and self.documents:
            self.documents["business_license"] = self.business_license


class KYCResponse(BaseModel):
    id: UUID
    user_id: UUID
    business_name: str
    gst_number: str
    fssai_number: Optional[str] = None
    pan_number: Optional[str] = None  # legacy
    business_type: str
    status: str
    verified_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class KYCStatusResponse(BaseModel):
    kyc_status: str
    kycStatus: str  # camelCase alternative
    is_kyc_verified: bool  # Boolean alternative
    kyc_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None

