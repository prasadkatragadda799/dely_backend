from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class UserPaymentMethod(Base):
    """Saved payment method (card or UPI) for a user. Used at checkout."""
    __tablename__ = "user_payment_methods"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(String(20), nullable=False)  # 'card' | 'upi'

    # Card fields (nullable when type=upi)
    last4 = Column(String(4), nullable=True)
    brand = Column(String(50), nullable=True)  # Visa, Mastercard, RuPay, etc.
    expiry_month = Column(String(2), nullable=True)  # MM
    expiry_year = Column(String(4), nullable=True)   # YY or YYYY

    # UPI field (nullable when type=card)
    upi_id = Column(String(255), nullable=True)  # e.g. user@paytm, user@ybl

    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="payment_methods")
