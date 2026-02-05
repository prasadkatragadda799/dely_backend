from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class NotificationResponse(BaseModel):
    """Single notification for API response. Uses 'read' for app compatibility."""
    id: UUID
    type: str
    title: str
    message: str
    read: bool = Field(alias="is_read", serialization_alias="read")
    created_at: datetime
    data: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
        populate_by_name = True

