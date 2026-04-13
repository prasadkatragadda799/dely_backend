from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.schemas.product import ProductListResponse


class CartItemAdd(BaseModel):
    """POST /cart body — Pydantic v2: use aliases so mobile snake_case and camelCase both work."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    product_id: UUID = Field(validation_alias=AliasChoices("product_id", "productId"))
    quantity: int
    price_option_key: str = Field(
        default="unit",
        validation_alias=AliasChoices("price_option_key", "priceOptionKey"),
    )


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: int
    product: ProductListResponse
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime


class CartSummary(BaseModel):
    subtotal: float  # Changed from Decimal to float for JSON serialization
    discount: float
    delivery_charge: float
    tax: float
    total: float
    item_count: int = 0


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    summary: CartSummary
