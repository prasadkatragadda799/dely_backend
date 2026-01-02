"""
Admin Category Management Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import re


class AdminCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = Field(None, max_length=10)  # Emoji (1-2 characters)
    color: Optional[str] = Field(None, max_length=7)  # Hex color code
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if v is not None:
            # Validate hex color code
            if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
                raise ValueError('Color must be a valid hex color code (e.g., #1E6DD8)')
        return v
    
    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError('Icon must be 1-10 characters (emoji)')
        return v


class AdminCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=7)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if v is not None:
            if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
                raise ValueError('Color must be a valid hex color code (e.g., #1E6DD8)')
        return v
    
    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError('Icon must be 1-10 characters (emoji)')
        return v


class CategoryReorderItem(BaseModel):
    id: UUID
    display_order: int


class CategoryReorderRequest(BaseModel):
    categories: List[CategoryReorderItem]


class AdminCategoryResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    product_count: int = 0
    children: List['AdminCategoryResponse'] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


# Update forward reference
AdminCategoryResponse.model_rebuild()

