from sqlalchemy import Column, String, Text, Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class OfferType(str, enum.Enum):
    BANNER = "banner"
    TEXT = "text"
    COMPANY = "company"


class Offer(Base):
    __tablename__ = "offers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    type = Column(SQLEnum(OfferType), nullable=False)
    image = Column(String(500), nullable=True)
    # Note: image_url column removed - not present in database table
    # Use 'image' field instead
    # Note: company_id column doesn't exist in database table yet
    # Uncomment when migration adds company_id column to offers table
    # company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # Note: company_id column doesn't exist in database table yet
    # Relationship is commented out until migration adds company_id column
    # company = relationship("Company", backref="offers")
    
    # Property to support schema that expects image_url
    @property
    def image_url(self):
        """Alias for image field to support API schemas"""
        return self.image

