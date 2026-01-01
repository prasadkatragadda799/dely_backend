"""
Admin Category Management Schemas
"""
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class AdminCategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: int = 0


class AdminCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryReorderItem(BaseModel):
    id: UUID
    display_order: int


class CategoryReorderRequest(BaseModel):
    categories: List[CategoryReorderItem]


class AdminCategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    parent_id: Optional[UUID]
    icon: Optional[str]
    color: Optional[str]
    display_order: int
    is_active: bool
    product_count: int = 0
    children: List['AdminCategoryResponse'] = []
    
    class Config:
        from_attributes = True


# Update forward reference
AdminCategoryResponse.model_rebuild()

