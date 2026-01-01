"""
Admin Offer Management Schemas
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from app.models.offer import OfferType


class AdminOfferCreate(BaseModel):
    title: str
    type: OfferType
    description: Optional[str] = None
    image_url: Optional[str] = None
    company_id: Optional[UUID] = None
    valid_from: date
    valid_to: date
    is_active: bool = True


class AdminOfferUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[OfferType] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    company_id: Optional[UUID] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    is_active: Optional[bool] = None


class AdminOfferResponse(BaseModel):
    id: UUID
    title: str
    type: OfferType
    description: Optional[str]
    image_url: Optional[str]
    company: Optional[dict] = None
    valid_from: date
    valid_to: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

