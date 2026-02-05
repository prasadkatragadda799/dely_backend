from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal


class WalletBalanceResponse(BaseModel):
    """GET /user/wallet - balance and optional recent_transactions."""
    balance: float
    wallet_balance: Optional[float] = None  # alias for app
    currency: str = "INR"
    recent_transactions: Optional[List[dict]] = None
    transactions: Optional[List[dict]] = None  # alias for app


class AddMoneyRequest(BaseModel):
    """POST /user/wallet/add-money body."""
    amount: float = Field(..., gt=0, description="Amount to add in INR")


class AddMoneyResponse(BaseModel):
    """POST /user/wallet/add-money - payment_url optional."""
    payment_url: Optional[str] = None
    order_id: str
    transaction_id: Optional[str] = None
