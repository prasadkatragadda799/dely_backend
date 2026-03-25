from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.offer import OfferResponse
from app.schemas.common import ResponseModel
from app.models.offer import Offer, OfferType
from typing import Optional, List, Tuple, Any
from datetime import date

router = APIRouter()


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
    """Columns needed for public offer APIs (excludes updated_at for DBs missing that column)."""
    return (
        Offer.id,
        Offer.title,
        Offer.subtitle,
        Offer.description,
        Offer.type,
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
        subtitle,
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
        subtitle=subtitle,
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
    return list(db.execute(stmt).all())


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
            _subtitle,
            description,
            offer_type,
            image,
            valid_from,
            valid_to,
            _is_active,
            _created_at,
        ) = row
        offer_data = {
            "id": _id,
            "title": title,
            "description": description,
            "imageUrl": image,
            "validFrom": valid_from.isoformat(),
            "validTo": valid_to.isoformat(),
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

