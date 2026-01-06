"""
Admin Categories Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID
import logging
from app.database import get_db
from app.schemas.admin_category import (
    AdminCategoryCreate, AdminCategoryUpdate, AdminCategoryResponse,
    CategoryReorderRequest
)
from app.schemas.common import ResponseModel
from app.models.category import Category
from app.models.product import Product
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.utils.slug import generate_slug, make_unique_slug
from app.models.admin import Admin

router = APIRouter()
logger = logging.getLogger(__name__)


def get_category_product_count(db: Session, category_id: str, include_subcategories: bool = True) -> int:
    """Get product count for a category, including subcategories recursively"""
    try:
        # Get direct products
        count = db.query(func.count(Product.id)).filter(
            Product.category_id == category_id,
            Product.is_available == True
        ).scalar() or 0
        
        if include_subcategories:
            # Get all subcategories recursively
            subcategories = db.query(Category.id).filter(Category.parent_id == category_id).all()
            for subcat in subcategories:
                count += get_category_product_count(db, str(subcat.id), include_subcategories=True)
        
        return count
    except Exception as e:
        logger.error(f"Error getting product count for category {category_id}: {str(e)}")
        return 0  # Return 0 on error to prevent breaking the entire request


def build_category_tree(db: Session, categories: list, parent_id: Optional[str] = None) -> list:
    """Build hierarchical category tree with product counts"""
    result = []
    try:
        for cat in categories:
            # Compare as strings (both are now strings)
            cat_parent_id = str(cat.parent_id) if cat.parent_id else None
            if cat_parent_id == parent_id:
                # Get product count including subcategories
                try:
                    product_count = get_category_product_count(db, str(cat.id), include_subcategories=True)
                except Exception as e:
                    logger.error(f"Error getting product count for category {cat.id}: {str(e)}")
                    product_count = 0
                
                category_data = {
                    "id": str(cat.id),
                    "name": cat.name,
                    "description": getattr(cat, 'description', None),
                    "icon": cat.icon,
                    "color": cat.color,
                    "parentId": str(cat.parent_id) if cat.parent_id else None,
                    "displayOrder": cat.display_order or 0,
                    "isActive": cat.is_active if hasattr(cat, 'is_active') else True,
                    "image": getattr(cat, 'image', None),
                    "metaTitle": getattr(cat, 'meta_title', None),
                    "metaDescription": getattr(cat, 'meta_description', None),
                    "productCount": product_count,
                    "children": build_category_tree(db, categories, str(cat.id))
                }
                
                result.append(category_data)
        
        # Sort by display_order
        result.sort(key=lambda x: x.get("displayOrder", 0))
    except Exception as e:
        logger.error(f"Error building category tree: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return result


@router.get("", response_model=ResponseModel)
async def list_categories(
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all categories in hierarchical tree structure"""
    try:
        categories = db.query(Category).order_by(Category.display_order).all()
        
        # Build tree structure with product counts
        tree = build_category_tree(db, categories, parent_id=None)
        
        return ResponseModel(
            success=True,
            data=tree,
            message="Categories retrieved successfully"
        )
    except Exception as e:
        import traceback
        logger.error(f"Error listing categories: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving categories: {str(e)}"
        )


@router.get("/{category_id}", response_model=ResponseModel)
async def get_category(
    category_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get category details"""
    # Cast UUID to string to match database column type (String(36))
    category_id_str = str(category_id)
    category = db.query(Category).filter(Category.id == category_id_str).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get product count including subcategories
    product_count = get_category_product_count(db, category_id_str, include_subcategories=True)
    
    # Get children
    children = db.query(Category).filter(Category.parent_id == category_id).order_by(Category.display_order).all()
    children_data = []
    for c in children:
        child_count = get_category_product_count(db, c.id, include_subcategories=True)
        children_data.append({
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "icon": c.icon,
            "color": c.color,
            "parentId": str(c.parent_id) if c.parent_id else None,
            "displayOrder": c.display_order,
            "isActive": c.is_active,
            "image": c.image,
            "metaTitle": c.meta_title,
            "metaDescription": c.meta_description,
            "productCount": child_count,
            "children": []
        })
    
    category_data = {
        "id": str(category.id),
        "name": category.name,
        "description": getattr(category, 'description', None),
        "icon": category.icon,
        "color": category.color,
        "parentId": str(category.parent_id) if category.parent_id else None,
        "displayOrder": category.display_order,
        "isActive": category.is_active,
        "image": getattr(category, 'image', None),
        "metaTitle": getattr(category, 'meta_title', None),
        "metaDescription": getattr(category, 'meta_description', None),
        "productCount": product_count,
        "children": children_data,
        "createdAt": category.created_at.isoformat() if category.created_at else None,
        "updatedAt": category.updated_at.isoformat() if category.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=category_data,
        message="Category retrieved successfully"
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: AdminCategoryCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new category or subcategory"""
    # Check if category name already exists at the same parent level
    existing = db.query(Category).filter(
        Category.name == category_data.name,
        Category.parent_id == category_data.parent_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists at this level"
        )
    
    # Generate slug if not provided
    slug = generate_slug(category_data.name)
    
    # Ensure slug is unique
    existing_slugs = [c.slug for c in db.query(Category.slug).all()]
    slug = make_unique_slug(slug, existing_slugs)
    
    # Validate parent_id if provided
    if category_data.parent_id:
        parent_id_str = str(category_data.parent_id)
        parent = db.query(Category).filter(Category.id == parent_id_str).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )
    
    category = Category(
        name=category_data.name,
        slug=slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
        icon=category_data.icon,
        color=category_data.color,
        display_order=category_data.display_order,
        is_active=category_data.is_active,
        meta_title=category_data.meta_title,
        meta_description=category_data.meta_description
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    # Log activity
    # Convert category.id (String) to UUID for entity_id
    try:
        entity_id_uuid = UUID(str(category.id)) if category.id else None
    except (ValueError, AttributeError):
        # If category.id is not a valid UUID format, try without dashes
        try:
            entity_id_uuid = UUID(str(category.id).replace('-', '')) if category.id else None
        except (ValueError, AttributeError):
            entity_id_uuid = None
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_created",
        entity_type="category",
        entity_id=entity_id_uuid,
        details={"name": category.name, "slug": category.slug},
        request=request
    )
    
    # Build response
    category_response = {
        "id": str(category.id),
        "name": category.name,
        "description": getattr(category, 'description', None),
        "icon": category.icon,
        "color": category.color,
        "parentId": str(category.parent_id) if category.parent_id else None,
        "displayOrder": category.display_order,
        "isActive": category.is_active,
        "image": getattr(category, 'image', None),
        "metaTitle": getattr(category, 'meta_title', None),
        "metaDescription": getattr(category, 'meta_description', None),
        "productCount": 0,
        "children": [],
        "createdAt": category.created_at.isoformat() if category.created_at else None,
        "updatedAt": category.updated_at.isoformat() if category.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=category_response,
        message="Category created successfully"
    )


@router.put("/{category_id}", response_model=ResponseModel)
async def update_category(
    category_id: UUID,
    category_data: AdminCategoryUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update an existing category"""
    # Cast UUID to string to match database column type (String(36))
    category_id_str = str(category_id)
    category = db.query(Category).filter(Category.id == category_id_str).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check name uniqueness if name is being updated
    if category_data.name and category_data.name != category.name:
        existing = db.query(Category).filter(
            Category.name == category_data.name,
            Category.parent_id == category.parent_id,
            Category.id != category_id_str
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category name already exists at this level"
            )
    
    # Prevent circular parent reference
    if category_data.parent_id == category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category cannot be its own parent"
        )
    
    # Validate parent_id if being updated
    if category_data.parent_id is not None and category_data.parent_id != category.parent_id:
        parent_id_str = str(category_data.parent_id)
        parent = db.query(Category).filter(Category.id == parent_id_str).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )
        
        # Check for circular reference in hierarchy
        current_parent_id = parent_id_str
        visited = {category_id_str}
        while current_parent_id:
            if current_parent_id in visited:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Circular reference detected in category hierarchy"
                )
            visited.add(current_parent_id)
            parent_cat = db.query(Category).filter(Category.id == current_parent_id).first()
            current_parent_id = str(parent_cat.parent_id) if parent_cat and parent_cat.parent_id else None
    
    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(category, key):
            setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    
    # Get product count
    product_count = get_category_product_count(db, category_id, include_subcategories=True)
    
    # Get children
    children = db.query(Category).filter(Category.parent_id == category_id).order_by(Category.display_order).all()
    children_data = []
    for c in children:
        child_count = get_category_product_count(db, c.id, include_subcategories=True)
        children_data.append({
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "icon": c.icon,
            "color": c.color,
            "parentId": str(c.parent_id) if c.parent_id else None,
            "displayOrder": c.display_order,
            "isActive": c.is_active,
            "image": c.image,
            "metaTitle": c.meta_title,
            "metaDescription": c.meta_description,
            "productCount": child_count,
            "children": []
        })
    
    # Log activity
    # Convert category_id_str (String) to UUID for entity_id
    try:
        entity_id_uuid = UUID(category_id_str) if category_id_str else None
    except (ValueError, AttributeError):
        # If category_id_str is not a valid UUID format, try without dashes
        try:
            entity_id_uuid = UUID(category_id_str.replace('-', '')) if category_id_str else None
        except (ValueError, AttributeError):
            entity_id_uuid = None
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_updated",
        entity_type="category",
        entity_id=entity_id_uuid,
        details=update_data,
        request=request
    )
    
    # Build response
    category_response = {
        "id": str(category.id),
        "name": category.name,
        "description": getattr(category, 'description', None),
        "icon": category.icon,
        "color": category.color,
        "parentId": str(category.parent_id) if category.parent_id else None,
        "displayOrder": category.display_order,
        "isActive": category.is_active,
        "image": getattr(category, 'image', None),
        "metaTitle": getattr(category, 'meta_title', None),
        "metaDescription": getattr(category, 'meta_description', None),
        "productCount": product_count,
        "children": children_data,
        "updatedAt": category.updated_at.isoformat() if category.updated_at else None
    }
    
    return ResponseModel(
        success=True,
        data=category_response,
        message="Category updated successfully"
    )


@router.delete("/{category_id}", response_model=ResponseModel)
async def delete_category(
    category_id: UUID,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Delete a category"""
    # Cast UUID to string to match database column type (String(36))
    category_id_str = str(category_id)
    category = db.query(Category).filter(Category.id == category_id_str).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check if category has children
    children_count = db.query(func.count(Category.id)).filter(
        Category.parent_id == category_id_str
    ).scalar() or 0
    
    if children_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete category with child categories. Please delete or move children first."
        )
    
    # Check if category has products (including subcategories)
    products_count = get_category_product_count(db, category_id_str, include_subcategories=True)
    
    if products_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete category with products. Please remove or reassign products first."
        )
    
    category_name = category.name
    db.delete(category)
    db.commit()
    
    # Log activity
    # Convert category_id_str (String) to UUID for entity_id
    try:
        entity_id_uuid = UUID(category_id_str) if category_id_str else None
    except (ValueError, AttributeError):
        # If category_id_str is not a valid UUID format, try without dashes
        try:
            entity_id_uuid = UUID(category_id_str.replace('-', '')) if category_id_str else None
        except (ValueError, AttributeError):
            entity_id_uuid = None
    
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_deleted",
        entity_type="category",
        entity_id=entity_id_uuid,
        details={"name": category_name},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=None,
        message="Category deleted successfully"
    )


@router.put("/reorder", response_model=ResponseModel)
async def reorder_categories(
    reorder_data: CategoryReorderRequest,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Reorder categories"""
    for item in reorder_data.categories:
        category = db.query(Category).filter(Category.id == str(item.id)).first()
        if category:
            category.display_order = item.display_order
    
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="categories_reordered",
        entity_type="category",
        details={"count": len(reorder_data.categories)},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Categories reordered successfully"
    )

