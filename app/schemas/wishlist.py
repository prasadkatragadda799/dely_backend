from pydantic import BaseModel
from typing import List
from datetime import datetime
from uuid import UUID
from app.schemas.product import ProductListResponse


class WishlistAdd(BaseModel):
    product_id: UUID


class WishlistResponse(BaseModel):
    id: UUID
    product_id: UUID
    product: ProductListResponse
    created_at: datetime
    
    class Config:
        from_attributes = True

