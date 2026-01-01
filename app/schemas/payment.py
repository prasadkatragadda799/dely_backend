from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from decimal import Decimal


class PaymentInitiate(BaseModel):
    order_id: UUID
    amount: Decimal
    payment_method: str
    payment_details: Optional[Dict[str, Any]] = None


class PaymentInitiateResponse(BaseModel):
    payment_id: str
    payment_url: Optional[str] = None
    status: str


class PaymentVerify(BaseModel):
    payment_id: str
    transaction_id: str


class PaymentVerifyResponse(BaseModel):
    payment_status: str
    order_id: UUID

