from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # 'login', 'order', 'view_product', 'app_open', etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    location_city = Column(String(255), nullable=True, index=True)
    location_state = Column(String(255), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    
    # Composite indexes for better query performance
    __table_args__ = (
        Index('idx_user_activity_location', 'location_city', 'location_state'),
        Index('idx_user_activity_user_date', 'user_id', 'created_at'),
    )
