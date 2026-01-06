from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.offer import OfferResponse
from app.schemas.common import ResponseModel
from app.models.offer import Offer, OfferType
from typing import Optional
from datetime import date

router = APIRouter()


@router.get("", response_model=ResponseModel)
def get_offers(
    type_filter: Optional[str] = None,
    active: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Get all active offers (Mobile App API)"""
    today = date.today()
    query = db.query(Offer).filter(
        Offer.is_active == True,
        Offer.valid_from <= today,
        Offer.valid_to >= today
    )
    
    if type_filter:
        try:
            offer_type = OfferType(type_filter)
            query = query.filter(Offer.type == offer_type)
        except ValueError:
            pass
    
    offers = query.order_by(Offer.created_at.desc()).all()
    
    # Group by type
    banners = []
    text_offers = []
    company_offers = []
    
    for offer in offers:
        offer_data = {
            "id": offer.id,
            "title": offer.title,
            "description": offer.description,
            "imageUrl": offer.image,  # Use image field (image_url column doesn't exist in DB)
            "validFrom": offer.valid_from.isoformat(),
            "validTo": offer.valid_to.isoformat()
        }
        
        if offer.type == OfferType.BANNER:
            banners.append(offer_data)
        elif offer.type == OfferType.TEXT:
            text_offers.append(offer_data)
        elif offer.type == OfferType.COMPANY:
            if offer.company:
                offer_data["company"] = {
                    "id": offer.company.id,
                    "name": offer.company.name
                }
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
    today = date.today()
    offers = db.query(Offer).filter(
        Offer.type == OfferType.COMPANY,
        Offer.is_active == True,
        Offer.valid_from <= today,
        Offer.valid_to >= today
    ).order_by(Offer.created_at.desc()).all()
    
    return ResponseModel(
        success=True,
        data=[OfferResponse.model_validate(o) for o in offers]
    )


@router.get("/text-slides", response_model=ResponseModel)
def get_text_slides(db: Session = Depends(get_db)):
    """Get text slide offers"""
    today = date.today()
    offers = db.query(Offer).filter(
        Offer.type == OfferType.TEXT,
        Offer.is_active == True,
        Offer.valid_from <= today,
        Offer.valid_to >= today
    ).order_by(Offer.created_at.desc()).all()
    
    return ResponseModel(
        success=True,
        data=[OfferResponse.model_validate(o) for o in offers]
    )

