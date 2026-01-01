from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CategoryBase(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[UUID] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]
    color: Optional[str]
    parent_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    children: Optional[List['CategoryResponse']] = None

