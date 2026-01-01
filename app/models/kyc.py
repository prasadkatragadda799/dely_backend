from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class KYC(Base):
    __tablename__ = "kycs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False)
    gst_number = Column(String(15), nullable=False)
    pan_number = Column(String(10), nullable=False)
    business_type = Column(String(50), nullable=False)
    address = Column(JSON, nullable=False)
    documents = Column(JSON, nullable=True)
    status = Column(SQLEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="kyc_records")

