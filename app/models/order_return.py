from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class OrderReturn(Base):
    __tablename__ = "order_returns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Customer-filled fields
    status = Column(String(30), default="requested", nullable=False)
    # requested | approved | rejected | pickup_assigned | picked_up | received_at_hub
    reason = Column(Text, nullable=False)
    media_urls = Column(JSON, nullable=True)  # [{"url": "...", "type": "image"|"video"}]

    # Bank details for COD refund
    bank_account_number = Column(String(40), nullable=True)
    bank_ifsc_code = Column(String(15), nullable=True)
    bank_account_holder = Column(String(100), nullable=True)
    bank_name = Column(String(100), nullable=True)

    # Admin review
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Delivery pickup
    delivery_person_id = Column(String(36), ForeignKey("delivery_persons.id", ondelete="SET NULL"), nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    received_at_hub_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="return_request")
    user = relationship("User")
    delivery_person = relationship("DeliveryPerson")
