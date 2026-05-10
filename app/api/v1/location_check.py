"""
Customer-facing endpoint to check if a pincode is within the serviceable area.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ResponseModel
from app.models.settings import Settings

router = APIRouter()


def _get_service_location_settings(db: Session) -> dict:
    setting = db.query(Settings).filter(Settings.key == "service_locations").first()
    return setting.value if setting else {}


@router.get("/check", response_model=ResponseModel)
def check_location_availability(
    pincode: str = Query(..., description="6-digit pincode to check for delivery availability"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if a given pincode is within the serviceable area.
    Returns available=True when restrictions are disabled or the pincode is whitelisted.
    """
    service_settings = _get_service_location_settings(db)

    if not service_settings.get("enabled", False):
        return ResponseModel(
            success=True,
            data={"available": True, "restricted": False, "pincode": pincode.strip()},
            message="Delivery available"
        )

    locations = service_settings.get("locations", [])
    if not locations:
        return ResponseModel(
            success=True,
            data={"available": True, "restricted": False, "pincode": pincode.strip()},
            message="Delivery available"
        )

    allowed_pincodes = {loc["pincode"].strip() for loc in locations if loc.get("pincode")}
    available = pincode.strip() in allowed_pincodes

    return ResponseModel(
        success=True,
        data={"available": available, "restricted": True, "pincode": pincode.strip()},
        message="Delivery available" if available else "Delivery not available in your location"
    )
