from pydantic import BaseModel
from decimal import Decimal


class QuickStatsResponse(BaseModel):
    total_orders: int
    total_spent: Decimal
    pending_orders: int
    savings: Decimal

