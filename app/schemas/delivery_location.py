"""
Customer Delivery Location Schemas (for user addresses)
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class DeliveryLocationCreate(BaseModel):
    address: Optional[str] = None  # Legacy support
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None  # Legacy support
    city: str
    state: str
    pincode: str
    type: str = Field(default="home")  # home, office, other
    is_default: bool = Field(default=False)


class DeliveryLocationResponse(BaseModel):
    id: str
    user_id: str
    address: str
    address_line1: str
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str
    type: str
    is_default: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class DeliveryCheck(BaseModel):
    pincode: str = Field(min_length=6, max_length=6)


class DeliveryAvailabilityResponse(BaseModel):
    is_available: bool
    estimated_days: int
    delivery_charge: Decimal
    
    class Config:
        from_attributes = True
