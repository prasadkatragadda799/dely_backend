from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CANCELED = "canceled"  # Alternative spelling


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    delivery_person_id = Column(String(36), ForeignKey("delivery_persons.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method = Column(String(50), nullable=True)
    payment_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'paid', 'failed', 'refunded'
    items = Column(JSON, nullable=True)  # Legacy: Store order items as JSON (deprecated, use order_items relationship)
    delivery_address = Column(JSON, nullable=False)
    payment_details = Column(JSON, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), default=0.0, nullable=False)
    delivery_charge = Column(Numeric(10, 2), default=0.0, nullable=False)
    tax = Column(Numeric(10, 2), default=0.0, nullable=False)
    # Backward/forward compatibility:
    # - Original DB schema uses `total` (NOT NULL)
    # - Later migrations added `total_amount` (may be NULL in existing DBs)
    total_amount = Column(Numeric(10, 2), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # DB-required field (original schema)
    total = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    delivery_person = relationship("DeliveryPerson")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusHistory.created_at")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    # Note: product_name and product_image_url columns don't exist in database table yet
    # Uncomment when migration adds these columns
    # product_name = Column(String(255), nullable=False)  # Snapshot at time of order
    # product_image_url = Column(String(500), nullable=True)
    quantity = Column(Integer, nullable=False)
    # Note: unit_price column doesn't exist in database table yet
    # Use 'price' field instead (which exists in DB)
    # unit_price = Column(Numeric(10, 2), nullable=False)  # Price per unit at time of order
    subtotal = Column(Numeric(10, 2), nullable=False)
    # Note: created_at column doesn't exist in database table yet
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Legacy field - this exists in the database
    price = Column(Numeric(10, 2), nullable=True)  # Price per unit at time of order
    
    # Properties to support code that expects unit_price
    @property
    def unit_price(self):
        """Alias for price field"""
        return self.price
    
    @property
    def product_name(self):
        """Get product name from relationship if available"""
        return self.product.name if self.product else None
    
    @property
    def product_image_url(self):
        """Get product image URL from relationship if available"""
        if self.product and self.product.product_images:
            primary_image = next((img for img in self.product.product_images if img.is_primary), None)
            return primary_image.image_url if primary_image else (self.product.product_images[0].image_url if self.product.product_images else None)
        return None
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

