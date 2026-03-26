import logging

from fastapi import APIRouter, Depends
from sqlalchemy import cast, select, Text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.schemas.offer import OfferResponse
from app.schemas.common import ResponseModel
from app.models.offer import Offer, OfferType
from typing import Optional, List, Tuple, Any
from datetime import date, datetime

router = APIRouter()
logger = logging.getLogger(__name__)


def _format_offer_date(value: Any) -> Optional[str]:
    """ISO date string for JSON; handles date/datetime/str/None across DB drivers."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return str(value)


def _coerce_offer_type(value: Any) -> Optional[OfferType]:
    """Normalize DB/driver values to OfferType (handles enum name or value strings)."""
    if isinstance(value, OfferType):
        return value
    if isinstance(value, str):
        if value in OfferType.__members__:
            return OfferType[value]
        try:
            return OfferType(value)
        except ValueError:
            return None
    return None


def _active_offers_base_select():
    """Columns for public offer APIs: no subtitle (avoids failures if that column is missing in prod)."""
    return (
        Offer.id,
        Offer.title,
        Offer.description,
        cast(Offer.type, Text).label("offer_type_raw"),
        Offer.image,
        Offer.valid_from,
        Offer.valid_to,
        Offer.is_active,
        Offer.created_at,
    )


def _row_to_offer_response(row: Tuple[Any, ...]) -> OfferResponse:
    (
        oid,
        title,
        description,
        offer_type,
        image,
        valid_from,
        valid_to,
        is_active,
        created_at,
    ) = row
    coerced = _coerce_offer_type(offer_type)
    type_str = coerced.value if coerced is not None else str(offer_type)
    return OfferResponse(
        id=oid,
        title=title,
        subtitle=None,
        description=description,
        type=type_str,
        image=image,
        valid_from=valid_from,
        valid_to=valid_to,
        is_active=is_active,
        created_at=created_at,
    )


def _fetch_active_offer_rows(
    db: Session,
    *,
    type_filter: Optional[str] = None,
    offer_type_enum: Optional[OfferType] = None,
) -> List[Tuple[Any, ...]]:
    """Load active offers using an explicit column list so missing `updated_at` does not break queries."""
    today = date.today()
    cols = _active_offers_base_select()
    stmt = (
        select(*cols)
        .where(
            Offer.is_active == True,
            Offer.valid_from <= today,
            Offer.valid_to >= today,
        )
        .order_by(Offer.created_at.desc())
    )
    if offer_type_enum is not None:
        stmt = stmt.where(Offer.type == offer_type_enum)
    elif type_filter:
        try:
            ot = OfferType(type_filter)
            stmt = stmt.where(Offer.type == ot)
        except ValueError:
            pass
    try:
        return list(db.execute(stmt).all())
    except SQLAlchemyError:
        logger.exception("offers query failed")
        if settings.DEBUG:
            raise
        return []


@router.get("", response_model=ResponseModel)
def get_offers(
    type_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all active offers (Mobile App API)"""
    rows = _fetch_active_offer_rows(db, type_filter=type_filter)
    
    # Group by type
    banners = []
    text_offers = []
    company_offers = []
    
    for row in rows:
        (
            _id,
            title,
            description,
            offer_type,
            image,
            valid_from,
            valid_to,
            _is_active,
            _created_at,
        ) = row
        offer_data = {
            "id": str(_id) if _id is not None else None,
            "title": title,
            "description": description,
            "imageUrl": image,
            "validFrom": _format_offer_date(valid_from),
            "validTo": _format_offer_date(valid_to),
        }

        ot = _coerce_offer_type(offer_type)
        if ot == OfferType.BANNER:
            banners.append(offer_data)
        elif ot == OfferType.TEXT:
            text_offers.append(offer_data)
        elif ot == OfferType.COMPANY:
            company_offers.append(offer_data)
    
    return ResponseModel(
        success=True,
        data={
            "banners": banners,
            "textOffers": text_offers,
            "companyOffers": company_offers
        }
    )


@router.get("/company", response_model=ResponseModel)
def get_company_offers(db: Session = Depends(get_db)):
    """Get company offers"""
    rows = _fetch_active_offer_rows(db, offer_type_enum=OfferType.COMPANY)
    return ResponseModel(
        success=True,
        data=[_row_to_offer_response(r) for r in rows],
    )


@router.get("/text-slides", response_model=ResponseModel)
def get_text_slides(db: Session = Depends(get_db)):
    """Get text slide offers"""
    rows = _fetch_active_offer_rows(db, offer_type_enum=OfferType.TEXT)
    return ResponseModel(
        success=True,
        data=[_row_to_offer_response(r) for r in rows],
    )

