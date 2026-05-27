from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    pincodes = relationship("ZonePincode", back_populates="zone", cascade="all, delete-orphan")
    companies = relationship("Company", back_populates="zone")


class ZonePincode(Base):
    __tablename__ = "zone_pincodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    pincode = Column(String(10), nullable=False, index=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("zone_id", "pincode", name="uq_zone_pincode"),
        Index("ix_zone_pincodes_pincode", "pincode"),
    )

    # Relationships
    zone = relationship("Zone", back_populates="pincodes")
