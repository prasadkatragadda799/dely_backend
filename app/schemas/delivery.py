from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class DeliveryLocationBase(BaseModel):
    address: str
    city: str
    state: str
    pincode: str
    landmark: Optional[str] = None
    type: str  # home, office
    is_default: bool = False


class DeliveryLocationCreate(DeliveryLocationBase):
    pass


class DeliveryLocationResponse(BaseModel):
    id: UUID
    user_id: UUID
    address: str
    city: str
    state: str
    pincode: str
    landmark: Optional[str]
    type: str
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeliveryCheck(BaseModel):
    pincode: str


class DeliveryAvailabilityResponse(BaseModel):
    is_available: bool
    estimated_days: int
    delivery_charge: Decimal

