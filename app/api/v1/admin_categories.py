"""
Admin Categories Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID
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


def build_category_tree(categories: list, parent_id: Optional[UUID] = None) -> list:
    """Build hierarchical category tree"""
    result = []
    for cat in categories:
        if cat.parent_id == parent_id:
            # Get product count
            product_count = len([p for p in cat.products if p.is_available]) if hasattr(cat, 'products') else 0
            
            category_data = {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "icon": cat.icon,
                "color": cat.color,
                "displayOrder": cat.display_order,
                "isActive": cat.is_active,
                "productCount": product_count,
                "children": build_category_tree(categories, cat.id)
            }
            
            if cat.parent_id:
                category_data["parentId"] = cat.parent_id
            
            result.append(category_data)
    
    # Sort by display_order
    result.sort(key=lambda x: x["displayOrder"])
    return result


@router.get("", response_model=ResponseModel)
async def list_categories(
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all categories in tree structure"""
    categories = db.query(Category).all()
    
    # Build tree structure
    tree = build_category_tree(categories, parent_id=None)
    
    return ResponseModel(
        success=True,
        data=tree,
        message="Categories retrieved successfully"
    )


@router.get("/{category_id}", response_model=ResponseModel)
async def get_category(
    category_id: UUID,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get category details"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get product count
    product_count = db.query(func.count(Product.id)).filter(
        Product.category_id == category_id,
        Product.is_available == True
    ).scalar() or 0
    
    category_data = {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "parentId": category.parent_id,
        "icon": category.icon,
        "color": category.color,
        "displayOrder": category.display_order,
        "isActive": category.is_active,
        "productCount": product_count,
        "createdAt": category.created_at,
        "updatedAt": category.updated_at
    }
    
    if category.parent:
        category_data["parent"] = {
            "id": category.parent.id,
            "name": category.parent.name,
            "slug": category.parent.slug
        }
    
    # Get children
    children = db.query(Category).filter(Category.parent_id == category_id).all()
    category_data["children"] = [{
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "productCount": db.query(func.count(Product.id)).filter(
            Product.category_id == c.id,
            Product.is_available == True
        ).scalar() or 0
    } for c in children]
    
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
    """Create a new category"""
    # Generate slug if not provided
    slug = category_data.slug or generate_slug(category_data.name)
    
    # Ensure slug is unique
    existing_slugs = [c.slug for c in db.query(Category.slug).all()]
    slug = make_unique_slug(slug, existing_slugs)
    
    # Validate parent_id if provided
    if category_data.parent_id:
        parent = db.query(Category).filter(Category.id == category_data.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail="Parent category not found"
            )
    
    category = Category(
        name=category_data.name,
        slug=slug,
        parent_id=category_data.parent_id,
        icon=category_data.icon,
        color=category_data.color,
        display_order=category_data.display_order,
        is_active=True
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_created",
        entity_type="category",
        entity_id=category.id,
        details={"name": category.name, "slug": category.slug},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminCategoryResponse.model_validate(category),
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
    """Update a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Prevent circular parent reference
    if category_data.parent_id == category_id:
        raise HTTPException(
            status_code=400,
            detail="Category cannot be its own parent"
        )
    
    # Validate parent_id if being updated
    if category_data.parent_id and category_data.parent_id != category.parent_id:
        parent = db.query(Category).filter(Category.id == category_data.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail="Parent category not found"
            )
        
        # Check for circular reference in hierarchy
        current_parent_id = category_data.parent_id
        visited = {category_id}
        while current_parent_id:
            if current_parent_id in visited:
                raise HTTPException(
                    status_code=400,
                    detail="Circular reference detected in category hierarchy"
                )
            visited.add(current_parent_id)
            parent_cat = db.query(Category).filter(Category.id == current_parent_id).first()
            current_parent_id = parent_cat.parent_id if parent_cat else None
    
    # Handle slug update
    if category_data.slug and category_data.slug != category.slug:
        existing_slugs = [c.slug for c in db.query(Category.slug).filter(
            Category.id != category_id
        ).all()]
        category_data.slug = make_unique_slug(category_data.slug, existing_slugs)
    
    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(category, key):
            setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_updated",
        entity_type="category",
        entity_id=category_id,
        details=update_data,
        request=request
    )
    
    return ResponseModel(
        success=True,
        data=AdminCategoryResponse.model_validate(category),
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
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has children
    children_count = db.query(func.count(Category.id)).filter(
        Category.parent_id == category_id
    ).scalar() or 0
    
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category with child categories. Please delete or move children first."
        )
    
    # Check if category has products
    products_count = db.query(func.count(Product.id)).filter(
        Product.category_id == category_id
    ).scalar() or 0
    
    if products_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category with products. Please remove or reassign products first."
        )
    
    category_name = category.name
    db.delete(category)
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="category_deleted",
        entity_type="category",
        entity_id=category_id,
        details={"name": category_name},
        request=request
    )
    
    return ResponseModel(
        success=True,
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
        category = db.query(Category).filter(Category.id == item.id).first()
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

