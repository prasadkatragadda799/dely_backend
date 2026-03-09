"""
Public API for divisions (e.g. Grocery, Kitchen).
Mobile app uses this to show verticals/tabs like Instamart in Swiggy.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.division import DivisionResponse
from app.schemas.common import ResponseModel
from app.models.division import Division

router = APIRouter()


@router.get("", response_model=ResponseModel)
def list_divisions(db: Session = Depends(get_db)):
    """List all active divisions. Mobile app uses this to show Grocery / Kitchen tabs."""
    divisions = (
        db.query(Division)
        .filter(Division.is_active == True)
        .order_by(Division.display_order, Division.name)
        .all()
    )
    return ResponseModel(
        success=True,
        data=[DivisionResponse.model_validate(d) for d in divisions]
    )
