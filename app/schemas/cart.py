from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.schemas.product import ProductListResponse


class CartItemBase(BaseModel):
    product_id: UUID = None
    productId: UUID = None  # Support camelCase
    quantity: int
    
    def __init__(self, **data):
        # Support both product_id and productId
        if 'productId' in data and 'product_id' not in data:
            data['product_id'] = data['productId']
        super().__init__(**data)


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
    subtotal: float  # Changed from Decimal to float for JSON serialization
    discount: float
    delivery_charge: float
    tax: float
    total: float
    item_count: int = 0


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    summary: CartSummary

