from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    
    # Use String(36) to match database column type (VARCHAR, not UUID)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    icon = Column(String(100), nullable=True)  # Emoji icon (1-2 characters)
    color = Column(String(7), nullable=True)  # Hex color code
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    image = Column(String(500), nullable=True)  # Category image URL
    meta_title = Column(String(255), nullable=True)  # SEO meta title
    meta_description = Column(Text, nullable=True)  # SEO meta description
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")

