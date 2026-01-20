from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    SELLER = "seller"  # Seller role - can only manage their own products
    SUPPORT = "support"


class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(AdminRole), default=AdminRole.SUPPORT, nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)  # For sellers
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", backref="sellers")  # For sellers
    created_products = relationship("Product", back_populates="creator", foreign_keys="Product.created_by")
    verified_kycs = relationship("User", back_populates="kyc_verifier", foreign_keys="User.kyc_verified_by")
    order_status_changes = relationship("OrderStatusHistory", back_populates="changed_by_admin")
    activity_logs = relationship("AdminActivityLog", back_populates="admin")

