from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)  # Product's division at add time
    price_option_key = Column(String(20), nullable=False, default="unit")  # unit | set | remaining
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="carts")
    product = relationship("Product", back_populates="cart_items")
    division = relationship("Division", back_populates="cart_items")

