from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Wishlist(Base):
    __tablename__ = "wishlists"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="wishlists")
    product = relationship("Product", back_populates="wishlists")

