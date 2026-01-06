from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    hsn_code = Column(String(50), nullable=True)
    set_pcs = Column(String(50), nullable=True)  # "Set/Pcs"
    weight = Column(String(50), nullable=True)
    mrp = Column(Numeric(10, 2), nullable=True)
    special_price = Column(Numeric(10, 2), nullable=True)
    free_item = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="variants")


