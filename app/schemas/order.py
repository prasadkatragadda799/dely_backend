from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int
    price: Optional[Decimal] = None  # Optional, will be fetched from product if not provided


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    delivery_location_id: Optional[UUID] = None  # Support delivery_location_id from frontend
    delivery_address: Optional[Dict[str, Any]] = None  # Support direct delivery_address
    payment_method: str
    payment_details: Optional[Dict[str, Any]] = None


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    quantity: int
    price: Optional[Decimal] = None
    subtotal: Decimal
    product_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    user_id: Optional[UUID] = None
    status: str
    # IMPORTANT:
    # - SQLAlchemy `Order` model has a legacy `items` JSON column that may be NULL
    # - The real list lives in the `order_items` relationship
    # So validate from `order_items` and always default to an empty list.
    items: List[OrderItemResponse] = Field(default_factory=list, validation_alias="order_items")
    delivery_address: Dict[str, Any]
    payment_method: str
    subtotal: Decimal
    discount: Decimal
    delivery_charge: Decimal
    tax: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    id: UUID
    order_number: str
    status: str
    total: Decimal
    # Some ORM Order objects don't expose items_count; default to 0 instead of failing validation.
    items_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderCancel(BaseModel):
    reason: Optional[str] = None


class OrderTracking(BaseModel):
    order_number: str
    status: str
    status_history: List[Dict[str, Any]]
    estimated_delivery: Optional[datetime] = None

