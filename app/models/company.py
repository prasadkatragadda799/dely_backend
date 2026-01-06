from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Company(Base):
    __tablename__ = "companies"
    
    # Use String(36) to match database column type (VARCHAR, not UUID)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Legacy field for backward compatibility
    logo = Column(String(500), nullable=True)  # Deprecated, use logo_url
    
    # Relationships
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
    brands = relationship("Brand", back_populates="company", cascade="all, delete-orphan")

