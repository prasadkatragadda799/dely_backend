"""
Admin Product Management Schemas
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from app.utils.packaging_label import format_variant_packaging_line


class AdminProductCreate(BaseModel):
    name: str
    slug: Optional[str] = None  # Auto-generated if not provided
    description: Optional[str] = None
    brand_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    division_id: Optional[UUID] = None  # Kitchen / Grocery; null = default
    mrp: Decimal = Field(..., gt=0)
    selling_price: Decimal = Field(..., gt=0)
    commission_cost: Decimal = Field(default=Decimal("0"), ge=0)
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
    division_id: Optional[UUID] = None
    mrp: Optional[Decimal] = Field(None, gt=0)
    selling_price: Optional[Decimal] = Field(None, gt=0)
    commission_cost: Optional[Decimal] = Field(None, ge=0)
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


class AdminProductVariantResponse(BaseModel):
    id: UUID
    hsnCode: Optional[str] = None
    packagingLabelType: Optional[str] = None
    setPieces: Optional[str] = None
    packagingLabel: Optional[str] = None
    weight: Optional[str] = None
    mrp: Optional[Decimal] = None
    specialPrice: Optional[Decimal] = None
    freeItem: Optional[str] = None

    class Config:
        from_attributes = True


class AdminProductResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    hsnCode: Optional[str] = None
    brand: Optional[Dict[str, Any]] = None
    company: Optional[Dict[str, Any]] = None
    category: Optional[Dict[str, Any]] = None
    division_id: Optional[UUID] = None
    mrp: Decimal
    selling_price: Decimal
    commission_cost: Decimal = Field(default=Decimal("0"))
    set_selling_price: Optional[Decimal] = None
    set_mrp: Optional[Decimal] = None
    remaining_selling_price: Optional[Decimal] = None
    remaining_mrp: Optional[Decimal] = None
    stock_quantity: int
    min_order_quantity: int
    unit: str
    pieces_per_set: int
    specifications: Optional[Dict[str, Any]]
    is_featured: bool
    is_available: bool
    expiry_date: Optional[date] = None
    images: List[ProductImageResponse] = Field(default_factory=list)
    variants: List[AdminProductVariantResponse] = Field(default_factory=list)
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
        # Prefer product-level HSN; fall back to the first variant that has one.
        hsn_code = getattr(obj, "hsn_code", None)
        if not hsn_code and hasattr(obj, "variants") and obj.variants:
            for v in obj.variants:
                hsn_code = getattr(v, "hsn_code", None)
                if hsn_code:
                    break

        data = {
            'id': obj.id,
            'name': obj.name,
            'slug': obj.slug,
            'description': obj.description,
            'hsnCode': hsn_code,
            'division_id': UUID(str(obj.division_id)) if getattr(obj, 'division_id', None) else None,
            'mrp': obj.mrp,
            'selling_price': obj.selling_price,
            'commission_cost': getattr(obj, 'commission_cost', Decimal("0")),
            'set_selling_price': getattr(obj, 'set_selling_price', None),
            'set_mrp': getattr(obj, 'set_mrp', None),
            'remaining_selling_price': getattr(obj, 'remaining_selling_price', None),
            'remaining_mrp': getattr(obj, 'remaining_mrp', None),
            'stock_quantity': obj.stock_quantity,
            'min_order_quantity': obj.min_order_quantity,
            'unit': obj.unit,
            'pieces_per_set': obj.pieces_per_set,
            'specifications': obj.specifications,
            'is_featured': obj.is_featured,
            'is_available': obj.is_available,
            'expiry_date': getattr(obj, 'expiry_date', None),
            'images': images,  # Always a list, never None
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
        }
        
        # Handle variants safely
        variants: List[AdminProductVariantResponse] = []
        if hasattr(obj, "variants") and obj.variants:
            for v in obj.variants:
                try:
                    ptype = getattr(v, "packaging_label_type", None)
                    set_pcs = getattr(v, "set_pcs", None)
                    wgt = getattr(v, "weight", None)
                    variants.append(
                        AdminProductVariantResponse(
                            id=UUID(str(v.id)),
                            hsnCode=getattr(v, "hsn_code", None),
                            packagingLabelType=ptype,
                            setPieces=set_pcs,
                            packagingLabel=format_variant_packaging_line(ptype, set_pcs, wgt),
                            weight=wgt,
                            mrp=getattr(v, "mrp", None),
                            specialPrice=getattr(v, "special_price", None),
                            freeItem=getattr(v, "free_item", None),
                        )
                    )
                except Exception:
                    continue

        data["variants"] = variants

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

    @field_validator("variants", mode="before")
    @classmethod
    def validate_variants(cls, v):
        """Ensure variants is always a list, never None"""
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

