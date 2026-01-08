from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, TypeDecorator
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class KYCStatus(str, enum.Enum):
    NOT_VERIFIED = "not_verified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class KYCStatusType(TypeDecorator):
    """Type decorator to ensure enum values are used instead of names"""
    impl = String
    cache_ok = True
    
    def __init__(self):
        super().__init__(50)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, KYCStatus):
            return value.value  # Use enum value, not name
        return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Try to convert to enum, handling both uppercase and lowercase
        value_str = str(value).lower()  # Normalize to lowercase
        try:
            return KYCStatus(value_str)
        except ValueError:
            # If exact match fails, try case-insensitive match
            for status in KYCStatus:
                if status.value.lower() == value_str:
                    return status
            # If still no match, return the value as-is (shouldn't happen in normal operation)
            return value


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
    kyc_status = Column(KYCStatusType(), default=KYCStatus.NOT_VERIFIED, nullable=False)
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

