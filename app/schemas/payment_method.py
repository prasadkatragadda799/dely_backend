from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal


class PaymentMethodCreate(BaseModel):
    """Add a saved payment method (card or UPI)."""
    type: Literal["card", "upi"]

    # Card fields
    last4: Optional[str] = Field(None, max_length=4, min_length=4)
    brand: Optional[str] = Field(None, max_length=50)
    expiry_month: Optional[str] = Field(None, max_length=2, min_length=2)
    expiry_year: Optional[str] = Field(None, max_length=4, min_length=2)

    # UPI field
    upi_id: Optional[str] = Field(None, max_length=255)

    is_default: bool = False

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "card":
            if not self.last4 or not self.brand:
                raise ValueError("Card requires last4 and brand")
            if not self.expiry_month or not self.expiry_year:
                raise ValueError("Card requires expiry_month and expiry_year")
        elif self.type == "upi":
            if not self.upi_id or not self.upi_id.strip():
                raise ValueError("UPI requires upi_id")
        return self


class PaymentMethodResponse(BaseModel):
    """Single payment method as returned by API."""
    id: str
    type: str
    last4: Optional[str] = None
    brand: Optional[str] = None
    expiry_month: Optional[str] = None
    expiry_year: Optional[str] = None
    upi_id: Optional[str] = None
    is_default: bool

    class Config:
        from_attributes = True


class PaymentMethodSetDefaultResponse(BaseModel):
    """Response for set-default endpoint."""
    id: str
    is_default: bool = True
