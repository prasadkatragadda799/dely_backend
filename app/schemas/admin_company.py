"""
Admin Company & Brand Management Schemas
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AdminCompanyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None


class AdminCompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None


class AdminCompanyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    total_products: int = 0
    total_brands: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AdminBrandCreate(BaseModel):
    name: str
    company_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    logo_url: Optional[str] = None


class AdminBrandUpdate(BaseModel):
    name: Optional[str] = None
    company_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    logo_url: Optional[str] = None


class AdminBrandResponse(BaseModel):
    id: UUID
    name: str
    company: Optional[dict] = None
    category: Optional[dict] = None
    logo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

