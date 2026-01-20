from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    mrp = Column(Numeric(10, 2), nullable=False)  # Maximum Retail Price
    selling_price = Column(Numeric(10, 2), nullable=False)  # Selling Price
    stock_quantity = Column(Integer, default=0, nullable=False)
    min_order_quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String(50), nullable=False)
    pieces_per_set = Column(Integer, default=1, nullable=False)
    hsn_code = Column(String(50), nullable=True)  # HSN code for GST/tax
    specifications = Column(JSON, nullable=True)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("admins.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Legacy fields for backward compatibility (can be removed later)
    brand = Column(String(255), nullable=True, index=True)  # Deprecated, use brand_id
    price = Column(Numeric(10, 2), nullable=True)  # Deprecated, use selling_price
    original_price = Column(Numeric(10, 2), nullable=True)  # Deprecated, use mrp
    discount = Column(Integer, default=0, nullable=True)  # Deprecated, calculate from mrp/selling_price
    images = Column(JSON, nullable=True)  # Deprecated, use product_images relationship
    stock = Column(Integer, default=0, nullable=True)  # Deprecated, use stock_quantity
    min_order = Column(Integer, default=1, nullable=True)  # Deprecated, use min_order_quantity
    rating = Column(Numeric(3, 2), default=0.0, nullable=True)  # For future reviews feature
    reviews_count = Column(Integer, default=0, nullable=True)  # For future reviews feature
    
    # Constraints
    __table_args__ = (
        CheckConstraint('selling_price <= mrp', name='check_selling_price_lte_mrp'),
    )
    
    # Relationships
    brand_rel = relationship("Brand", back_populates="products", foreign_keys=[brand_id])
    company = relationship("Company", back_populates="products")
    category = relationship("Category", back_populates="products")
    creator = relationship("Admin", back_populates="created_products", foreign_keys=[created_by])
    product_images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("Cart", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    wishlists = relationship("Wishlist", back_populates="product", cascade="all, delete-orphan")

