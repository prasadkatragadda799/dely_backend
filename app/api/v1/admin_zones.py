"""
Admin Zone Management Endpoints
Zones group pincodes; companies assigned to a zone are only visible to users in that zone.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.zone import Zone, ZonePincode
from app.models.company import Company
from app.api.admin_deps import require_manager_or_above
from app.models.admin import Admin
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic schemas ────────────────────────────────────────────────────────

class ZoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PincodeAdd(BaseModel):
    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None


class PincodesAdd(BaseModel):
    pincodes: List[PincodeAdd]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _zone_to_dict(zone: Zone, include_pincodes: bool = True) -> dict:
    data = {
        "id": zone.id,
        "name": zone.name,
        "description": zone.description,
        "isActive": zone.is_active,
        "createdAt": zone.created_at,
        "updatedAt": zone.updated_at,
    }
    if include_pincodes:
        data["pincodes"] = [
            {"id": zp.id, "pincode": zp.pincode, "city": zp.city, "state": zp.state}
            for zp in zone.pincodes
        ]
        data["totalPincodes"] = len(zone.pincodes)
    return data


# ── Zone CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=ResponseModel)
async def list_zones(
    active_only: bool = Query(False),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """List all zones with their pincodes and linked company count."""
    query = db.query(Zone)
    if active_only:
        query = query.filter(Zone.is_active == True)
    zones = query.order_by(Zone.name).all()

    result = []
    for zone in zones:
        d = _zone_to_dict(zone)
        d["totalCompanies"] = db.query(func.count(Company.id)).filter(
            Company.zone_id == zone.id
        ).scalar() or 0
        result.append(d)

    return ResponseModel(success=True, data=result, message="Zones retrieved successfully")


@router.get("/{zone_id}", response_model=ResponseModel)
async def get_zone(
    zone_id: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    d = _zone_to_dict(zone)
    d["companies"] = [
        {"id": c.id, "name": c.name, "logoUrl": c.logo_url or c.logo}
        for c in zone.companies
    ]
    return ResponseModel(success=True, data=d, message="Zone retrieved successfully")


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_zone(
    payload: ZoneCreate,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Create a new delivery zone."""
    existing = db.query(Zone).filter(func.lower(Zone.name) == func.lower(payload.name.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail="Zone with this name already exists")

    zone = Zone(
        name=payload.name.strip(),
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    return ResponseModel(success=True, data=_zone_to_dict(zone), message="Zone created successfully")


@router.put("/{zone_id}", response_model=ResponseModel)
async def update_zone(
    zone_id: str,
    payload: ZoneUpdate,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    if payload.name is not None:
        name_stripped = payload.name.strip()
        conflict = db.query(Zone).filter(
            func.lower(Zone.name) == func.lower(name_stripped),
            Zone.id != zone_id,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Zone with this name already exists")
        zone.name = name_stripped

    if payload.description is not None:
        zone.description = payload.description
    if payload.is_active is not None:
        zone.is_active = payload.is_active

    db.commit()
    db.refresh(zone)
    return ResponseModel(success=True, data=_zone_to_dict(zone), message="Zone updated successfully")


@router.delete("/{zone_id}", response_model=ResponseModel)
async def delete_zone(
    zone_id: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # Unlink companies before deleting (SET NULL via FK cascade handles it)
    db.delete(zone)
    db.commit()
    return ResponseModel(success=True, message="Zone deleted successfully")


# ── Zone Pincodes ─────────────────────────────────────────────────────────────

@router.post("/{zone_id}/pincodes", response_model=ResponseModel)
async def add_pincodes_to_zone(
    zone_id: str,
    payload: PincodesAdd,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Add one or more pincodes to a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    added = []
    skipped = []
    for item in payload.pincodes:
        pincode = item.pincode.strip()
        existing = db.query(ZonePincode).filter(
            ZonePincode.zone_id == zone_id,
            ZonePincode.pincode == pincode,
        ).first()
        if existing:
            skipped.append(pincode)
            continue

        # If pincode already belongs to another zone, reject it
        conflict = db.query(ZonePincode).filter(
            ZonePincode.pincode == pincode,
            ZonePincode.zone_id != zone_id,
        ).first()
        if conflict:
            raise HTTPException(
                status_code=400,
                detail=f"Pincode {pincode} already belongs to another zone. Remove it first.",
            )

        zp = ZonePincode(zone_id=zone_id, pincode=pincode, city=item.city, state=item.state)
        db.add(zp)
        added.append(pincode)

    db.commit()
    db.refresh(zone)

    return ResponseModel(
        success=True,
        data=_zone_to_dict(zone),
        message=f"Added {len(added)} pincode(s). Skipped {len(skipped)} duplicate(s).",
    )


@router.delete("/{zone_id}/pincodes/{pincode}", response_model=ResponseModel)
async def remove_pincode_from_zone(
    zone_id: str,
    pincode: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """Remove a pincode from a zone."""
    zp = db.query(ZonePincode).filter(
        ZonePincode.zone_id == zone_id,
        ZonePincode.pincode == pincode.strip(),
    ).first()
    if not zp:
        raise HTTPException(status_code=404, detail="Pincode not found in this zone")

    db.delete(zp)
    db.commit()
    return ResponseModel(success=True, message=f"Pincode {pincode} removed from zone")


# ── Zone → Company assignment ─────────────────────────────────────────────────

@router.get("/{zone_id}/companies", response_model=ResponseModel)
async def list_zone_companies(
    zone_id: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    companies = db.query(Company).filter(Company.zone_id == zone_id).all()
    return ResponseModel(
        success=True,
        data=[{"id": c.id, "name": c.name, "logoUrl": c.logo_url or c.logo} for c in companies],
        message="Companies in zone retrieved successfully",
    )
