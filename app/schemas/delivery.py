from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class DeliveryLocationBase(BaseModel):
    address_line1: Optional[str] = None  # Support both formats
    address_line2: Optional[str] = None
    address: Optional[str] = None  # Legacy support - maps to address_line1
    city: str
    state: str
    pincode: str
    landmark: Optional[str] = None  # Legacy support - maps to address_line2
    type: str  # home, office, other
    is_default: bool = False
    
    def __init__(self, **data):
        # Support both address_line1/address_line2 and address/landmark
        if 'address' in data and 'address_line1' not in data:
            data['address_line1'] = data['address']
        if 'landmark' in data and 'address_line2' not in data:
            data['address_line2'] = data['landmark']
        super().__init__(**data)


class DeliveryLocationCreate(DeliveryLocationBase):
    pass


class DeliveryLocationResponse(BaseModel):
    id: UUID
    user_id: UUID
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address: Optional[str] = None  # Legacy support
    city: str
    state: str
    pincode: str
    landmark: Optional[str] = None  # Legacy support
    type: str
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map address to address_line1 and landmark to address_line2
        data = {}
        if hasattr(obj, 'address'):
            data['address_line1'] = obj.address
            data['address'] = obj.address  # Legacy support
        if hasattr(obj, 'landmark'):
            data['address_line2'] = obj.landmark
            data['landmark'] = obj.landmark  # Legacy support
        if hasattr(obj, 'city'):
            data['city'] = obj.city
        if hasattr(obj, 'state'):
            data['state'] = obj.state
        if hasattr(obj, 'pincode'):
            data['pincode'] = obj.pincode
        if hasattr(obj, 'type'):
            data['type'] = obj.type
        if hasattr(obj, 'is_default'):
            data['is_default'] = obj.is_default
        if hasattr(obj, 'id'):
            data['id'] = obj.id
        if hasattr(obj, 'user_id'):
            data['user_id'] = obj.user_id
        if hasattr(obj, 'created_at'):
            data['created_at'] = obj.created_at
        if hasattr(obj, 'updated_at'):
            data['updated_at'] = obj.updated_at
        return cls(**data)


class DeliveryCheck(BaseModel):
    pincode: str


class DeliveryAvailabilityResponse(BaseModel):
    is_available: bool
    estimated_days: int
    delivery_charge: Decimal

