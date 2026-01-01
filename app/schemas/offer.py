from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class OfferBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    type: str
    image: Optional[str] = None
    valid_from: date
    valid_to: date


class OfferCreate(OfferBase):
    is_active: bool = True


class OfferResponse(BaseModel):
    id: UUID
    title: str
    subtitle: Optional[str]
    description: Optional[str]
    type: str
    image: Optional[str]
    valid_from: date
    valid_to: date
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

