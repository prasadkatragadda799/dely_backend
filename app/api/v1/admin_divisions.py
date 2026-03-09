"""
Admin Divisions CRUD (e.g. Grocery, Kitchen).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.schemas.admin_division import AdminDivisionCreate, AdminDivisionUpdate, AdminDivisionResponse
from app.schemas.common import ResponseModel
from app.models.division import Division
from app.api.admin_deps import require_manager_or_above, require_seller_or_above
from app.models.admin import Admin
from app.utils.slug import generate_slug

router = APIRouter()


@router.get("", response_model=ResponseModel)
def list_divisions(
    admin: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """List all divisions (for admin dropdowns and management)."""
    divisions = db.query(Division).order_by(Division.display_order, Division.name).all()
    return ResponseModel(
        success=True,
        data=[AdminDivisionResponse.model_validate(d) for d in divisions]
    )


@router.get("/{division_id}", response_model=ResponseModel)
def get_division(
    division_id: UUID,
    admin: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """Get a single division."""
    d = db.query(Division).filter(Division.id == str(division_id)).first()
    if not d:
        raise HTTPException(status_code=404, detail="Division not found")
    return ResponseModel(success=True, data=AdminDivisionResponse.model_validate(d))


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
def create_division(
    payload: AdminDivisionCreate,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new division (e.g. Kitchen)."""
    existing = db.query(Division).filter(Division.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Division with this slug already exists")
    division = Division(
        name=payload.name,
        slug=payload.slug.strip().lower(),
        description=payload.description,
        icon=payload.icon,
        image_url=payload.image_url,
        display_order=payload.display_order,
        is_active=payload.is_active
    )
    db.add(division)
    db.commit()
    db.refresh(division)
    return ResponseModel(success=True, data=AdminDivisionResponse.model_validate(division), message="Division created")


@router.patch("/{division_id}", response_model=ResponseModel)
def update_division(
    division_id: UUID,
    payload: AdminDivisionUpdate,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update a division."""
    d = db.query(Division).filter(Division.id == str(division_id)).first()
    if not d:
        raise HTTPException(status_code=404, detail="Division not found")
    if payload.name is not None:
        d.name = payload.name
    if payload.slug is not None:
        d.slug = payload.slug.strip().lower()
    if payload.description is not None:
        d.description = payload.description
    if payload.icon is not None:
        d.icon = payload.icon
    if payload.image_url is not None:
        d.image_url = payload.image_url
    if payload.display_order is not None:
        d.display_order = payload.display_order
    if payload.is_active is not None:
        d.is_active = payload.is_active
    db.commit()
    db.refresh(d)
    return ResponseModel(success=True, data=AdminDivisionResponse.model_validate(d), message="Division updated")
