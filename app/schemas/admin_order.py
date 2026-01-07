from pydantic import BaseModel
from typing import Optional


class OrderStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class OrderCancel(BaseModel):
    reason: str

