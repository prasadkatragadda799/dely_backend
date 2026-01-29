"""
Delivery Person Schemas
"""
from pydantic import BaseModel, EmailStr, Field, AliasChoices
from typing import Optional, List
from datetime import datetime


# Delivery Person Authentication
class DeliveryLogin(BaseModel):
    phone: str = Field(validation_alias=AliasChoices("phone", "phoneNumber", "phone_number"))
    password: str = Field(validation_alias=AliasChoices("password", "pass"))


class DeliveryPersonResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    employeeId: Optional[str] = None
    employee_id: Optional[str] = None
    vehicleNumber: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicleType: Optional[str] = None
    vehicle_type: Optional[str] = None
    isAvailable: bool
    is_available: bool
    isOnline: bool
    is_online: bool
    
    class Config:
        from_attributes = True


# Delivery Person Management (Admin)
class DeliveryPersonCreate(BaseModel):
    name: str
    phone: str = Field(pattern=r'^\+?[0-9]{10,15}$')
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6)
    employeeId: Optional[str] = None
    licenseNumber: Optional[str] = None
    vehicleNumber: Optional[str] = None
    vehicleType: Optional[str] = None


class DeliveryPersonUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    employeeId: Optional[str] = None
    licenseNumber: Optional[str] = None
    vehicleNumber: Optional[str] = None
    vehicleType: Optional[str] = None
    isActive: Optional[bool] = None
    isAvailable: Optional[bool] = None


# Availability Toggle
class AvailabilityRequest(BaseModel):
    available: bool


# Location Update
class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


# Order Assignment
class OrderAssignment(BaseModel):
    orderId: str
    deliveryPersonId: str


# Delivery Status Update
class DeliveryStatusUpdate(BaseModel):
    status: str  # picked_up, in_transit, arrived, delivered
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    photo: Optional[str] = None  # Base64 or URL for proof of delivery


# Delivery Order Response
class DeliveryOrderItem(BaseModel):
    productName: str
    quantity: int
    price: float


class DeliveryOrderResponse(BaseModel):
    id: str
    orderNumber: str
    order_number: str
    status: str
    customerName: str
    customer_name: str
    customerPhone: str
    customer_phone: str
    deliveryAddress: dict
    delivery_address: dict
    items: List[DeliveryOrderItem]
    totalAmount: float
    total_amount: float
    distance: Optional[float] = None  # Distance in km
    estimatedTime: Optional[int] = None  # Estimated time in minutes
    pickupAddress: Optional[dict] = None  # Warehouse/store address
    pickup_address: Optional[dict] = None
    createdAt: str
    created_at: str
