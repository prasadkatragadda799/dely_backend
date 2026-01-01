from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.schemas.product import ProductListResponse


class CartItemBase(BaseModel):
    product_id: UUID
    quantity: int


class CartItemAdd(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    product: ProductListResponse
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    subtotal: Decimal
    discount: Decimal
    delivery_charge: Decimal
    tax: Decimal
    total: Decimal


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    summary: CartSummary

