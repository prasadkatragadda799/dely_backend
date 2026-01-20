"""
Delivery Person Model
Handles delivery personnel who can log in to mobile app and deliver orders
"""
from sqlalchemy import Column, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class DeliveryPerson(Base):
    """
    Delivery person model for tracking delivery personnel
    """
    __tablename__ = "delivery_persons"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Identification
    employee_id = Column(String(50), unique=True, nullable=True)
    license_number = Column(String(50), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    vehicle_type = Column(String(50), nullable=True)  # bike, car, van, etc.
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)  # Available for new assignments
    is_online = Column(Boolean, default=False, nullable=False)  # Currently logged in
    
    # Current location (updated frequently)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    
    # Timestamps
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # This will be linked when we update the Order model
    # assigned_orders = relationship("Order", back_populates="delivery_person")
    
    def __repr__(self):
        return f"<DeliveryPerson {self.name} ({self.phone})>"
