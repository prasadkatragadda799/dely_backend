from pydantic import BaseModel
from typing import Optional, Dict, Any
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
    business_name: str
    gst_number: str
    pan_number: str
    business_type: str
    address: Dict[str, Any]
    documents: Optional[Dict[str, Any]] = None


class KYCResponse(BaseModel):
    id: UUID
    user_id: UUID
    business_name: str
    gst_number: str
    pan_number: str
    business_type: str
    status: str
    verified_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class KYCStatusResponse(BaseModel):
    kyc_status: str
    kyc_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None

