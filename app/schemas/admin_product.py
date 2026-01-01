"""
Admin Product Management Schemas
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class AdminProductCreate(BaseModel):
    name: str
    slug: Optional[str] = None  # Auto-generated if not provided
    description: Optional[str] = None
    brand_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    mrp: Decimal = Field(..., gt=0)
    selling_price: Decimal = Field(..., gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    min_order_quantity: int = Field(default=1, ge=1)
    unit: str
    pieces_per_set: int = Field(default=1, ge=1)
    specifications: Optional[Dict[str, Any]] = None
    is_featured: bool = False
    is_available: bool = True
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class AdminProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    brand_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    mrp: Optional[Decimal] = Field(None, gt=0)
    selling_price: Optional[Decimal] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    min_order_quantity: Optional[int] = Field(None, ge=1)
    unit: Optional[str] = None
    pieces_per_set: Optional[int] = Field(None, ge=1)
    specifications: Optional[Dict[str, Any]] = None
    is_featured: Optional[bool] = None
    is_available: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class AdminBulkProductUpdate(BaseModel):
    product_ids: List[UUID]
    updates: Dict[str, Any]  # e.g., {"stockQuantity": 100, "isAvailable": true}


class ProductImageResponse(BaseModel):
    id: UUID
    image_url: str
    display_order: int
    is_primary: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminProductResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    brand: Optional[Dict[str, Any]] = None
    company: Optional[Dict[str, Any]] = None
    category: Optional[Dict[str, Any]] = None
    mrp: Decimal
    selling_price: Decimal
    stock_quantity: int
    min_order_quantity: int
    unit: str
    pieces_per_set: int
    specifications: Optional[Dict[str, Any]]
    is_featured: bool
    is_available: bool
    images: List[ProductImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Handle images field - convert None to empty list
        images = []
        if hasattr(obj, 'product_images') and obj.product_images is not None:
            try:
                # If product_images relationship exists and is loaded, use it
                images = [ProductImageResponse.model_validate(img) for img in obj.product_images]
            except (AttributeError, TypeError):
                images = []
        elif hasattr(obj, 'images') and obj.images is not None:
            # Fallback to legacy images field if it exists
            if isinstance(obj.images, list):
                images = obj.images
            else:
                images = []
        
        # Create a dict with images handled
        data = {
            'id': obj.id,
            'name': obj.name,
            'slug': obj.slug,
            'description': obj.description,
            'mrp': obj.mrp,
            'selling_price': obj.selling_price,
            'stock_quantity': obj.stock_quantity,
            'min_order_quantity': obj.min_order_quantity,
            'unit': obj.unit,
            'pieces_per_set': obj.pieces_per_set,
            'specifications': obj.specifications,
            'is_featured': obj.is_featured,
            'is_available': obj.is_available,
            'images': images,  # Always a list, never None
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
        }
        
        # Handle relationships safely
        if hasattr(obj, 'brand_rel') and obj.brand_rel:
            data['brand'] = {'id': str(obj.brand_rel.id), 'name': obj.brand_rel.name}
        if hasattr(obj, 'company') and obj.company:
            data['company'] = {
                'id': str(obj.company.id),
                'name': obj.company.name,
                'logo_url': getattr(obj.company, 'logo_url', None)
            }
        if hasattr(obj, 'category') and obj.category:
            data['category'] = {
                'id': str(obj.category.id),
                'name': obj.category.name,
                'slug': getattr(obj.category, 'slug', None)
            }
        
        return cls(**data)
    
    @field_validator('images', mode='before')
    @classmethod
    def validate_images(cls, v):
        """Ensure images is always a list, never None"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []
    
    class Config:
        from_attributes = True
        populate_by_name = True


class AdminProductListResponse(BaseModel):
    products: List[AdminProductResponse]
    pagination: Dict[str, Any]

