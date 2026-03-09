"""Division model - e.g. Grocery (default) and Kitchen (Instamart-style vertical)."""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Division(Base):
    __tablename__ = "divisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)  # e.g. "Kitchen"
    slug = Column(String(100), unique=True, nullable=False, index=True)  # e.g. "kitchen"
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Emoji or icon name
    image_url = Column(String(500), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    categories = relationship("Category", back_populates="division")
    products = relationship("Product", back_populates="division")
    cart_items = relationship("Cart", back_populates="division")
