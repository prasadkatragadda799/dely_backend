from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class DivisionResponse(BaseModel):
    """Division as returned to mobile app (e.g. Grocery, Kitchen)."""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
