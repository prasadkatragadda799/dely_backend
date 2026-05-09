from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class ProductServiceArea(Base):
    __tablename__ = "product_service_areas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pincode = Column(String(10), nullable=False)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="service_areas")

    __table_args__ = (
        Index("ix_product_service_areas_product_pincode", "product_id", "pincode", unique=True),
    )
