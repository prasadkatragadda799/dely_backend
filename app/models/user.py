from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False)
    gst_number = Column(String(15), nullable=True)
    pan_number = Column(String(10), nullable=True)
    address = Column(JSON, nullable=True)
    kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_verified_by = Column(String(36), ForeignKey("admins.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    kyc_verifier = relationship("Admin", back_populates="verified_kycs", foreign_keys=[kyc_verified_by])
    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    wishlists = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    kyc_records = relationship("KYC", back_populates="user", cascade="all, delete-orphan")
    kyc_documents = relationship("KYCDocument", back_populates="user", cascade="all, delete-orphan")
    delivery_locations = relationship("DeliveryLocation", back_populates="user", cascade="all, delete-orphan")

