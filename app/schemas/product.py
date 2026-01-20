from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class ProductBase(BaseModel):
    name: str
    brand: str
    company_id: UUID
    category_id: UUID
    price: Decimal
    original_price: Decimal
    discount: int = 0
    images: Optional[List[str]] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    stock: int = 0
    min_order: int = 1
    unit: str
    pieces_per_set: int = 1


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount: Optional[int] = None
    stock: Optional[int] = None
    is_available: Optional[bool] = None
    is_featured: Optional[bool] = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    brand: str
    company_id: UUID
    category_id: UUID
    price: Decimal
    original_price: Decimal
    discount: int
    discount_percentage: Optional[float] = None  # Calculated discount percentage
    images: Optional[List[str]]
    description: Optional[str]
    specifications: Optional[Dict[str, Any]]
    stock: int
    min_order: int
    unit: str
    pieces_per_set: int
    rating: Decimal
    reviews_count: int
    is_available: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    id: UUID
    name: str
    brand: str
    price: Decimal
    original_price: Decimal
    discount: int
    discount_percentage: Optional[float] = None  # Calculated discount percentage
    images: Optional[List[str]]
    rating: Decimal
    is_available: bool
    is_featured: bool
    
    class Config:
        from_attributes = True

