from pydantic import BaseModel
from typing import List
from datetime import datetime
from uuid import UUID
from app.schemas.product import ProductListResponse


class WishlistAdd(BaseModel):
    product_id: UUID = None
    productId: UUID = None  # Support camelCase
    
    def __init__(self, **data):
        # Support both product_id and productId
        if 'productId' in data and 'product_id' not in data:
            data['product_id'] = data['productId']
        super().__init__(**data)


class WishlistResponse(BaseModel):
    id: UUID
    product_id: UUID
    product: ProductListResponse
    created_at: datetime
    
    class Config:
        from_attributes = True

