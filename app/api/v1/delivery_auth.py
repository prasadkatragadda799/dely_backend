"""
Delivery Person Authentication Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas.delivery import DeliveryLogin, DeliverySelfUpdate
from app.schemas.common import ResponseModel
from app.models.delivery_person import DeliveryPerson
from app.utils.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# Dependency to get current delivery person from token
async def get_current_delivery_person(
    request: Request,
    db: Session = Depends(get_db)
) -> DeliveryPerson:
    """Get current authenticated delivery person"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    delivery_person_id = payload.get("deliveryPersonId")
    if delivery_person_id is None:
        raise credentials_exception
    
    # Get delivery person from database
    delivery_person = db.query(DeliveryPerson).filter(
        DeliveryPerson.id == delivery_person_id
    ).first()
    
    if delivery_person is None or not delivery_person.is_active:
        raise credentials_exception
    
    return delivery_person


@router.post("/login", response_model=ResponseModel)
async def delivery_login(
    credentials: DeliveryLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delivery person login"""
    raw_identifier = (credentials.phone or "").strip()
    normalized_digits = "".join(ch for ch in raw_identifier if ch.isdigit())

    # Find delivery person by:
    # 1) exact phone as provided
    # 2) normalized digits phone variants (with/without country code)
    # 3) employee_id (partner id style login)
    phone_candidates = [raw_identifier] if raw_identifier else []
    if normalized_digits:
        phone_candidates.append(normalized_digits)
        if len(normalized_digits) == 10:
            phone_candidates.append(f"91{normalized_digits}")
            phone_candidates.append(f"+91{normalized_digits}")
        if len(normalized_digits) == 12 and normalized_digits.startswith("91"):
            phone_candidates.append(f"+{normalized_digits}")

    # Keep unique preserving order
    seen = set()
    phone_candidates = [p for p in phone_candidates if not (p in seen or seen.add(p))]

    delivery_person = db.query(DeliveryPerson).filter(
        (DeliveryPerson.phone.in_(phone_candidates)) |
        (DeliveryPerson.employee_id == raw_identifier)
    ).first()
    
    if not delivery_person or not verify_password(credentials.password, delivery_person.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password"
        )
    
    if not delivery_person.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact admin."
        )
    
    # Update last login and set online (best effort).
    # Login should not fail if these status fields have DB mismatch in older envs.
    try:
        delivery_person.last_login = datetime.utcnow()
        delivery_person.is_online = True
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Delivery login status update failed for %s: %s", delivery_person.id, e)
    
    # Create tokens
    token_data = {
        "deliveryPersonId": delivery_person.id,
        "phone": delivery_person.phone,
        "type": "delivery"
    }
    token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return ResponseModel(
        success=True,
        data={
            "token": token,
            "refreshToken": refresh_token,
            "deliveryPerson": {
                "id": delivery_person.id,
                "name": delivery_person.name,
                "phone": delivery_person.phone,
                "email": delivery_person.email,
                "employeeId": delivery_person.employee_id,
                "employee_id": delivery_person.employee_id,
                "vehicleNumber": delivery_person.vehicle_number,
                "vehicle_number": delivery_person.vehicle_number,
                "vehicleType": delivery_person.vehicle_type,
                "vehicle_type": delivery_person.vehicle_type,
                "isAvailable": delivery_person.is_available,
                "is_available": delivery_person.is_available,
                "isOnline": delivery_person.is_online,
                "is_online": delivery_person.is_online
            }
        },
        message="Login successful"
    )


@router.post("/logout", response_model=ResponseModel)
async def delivery_logout(
    delivery_person = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Delivery person logout"""
    delivery_person.is_online = False
    delivery_person.is_available = False
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Logout successful"
    )


@router.get("/me", response_model=ResponseModel)
async def get_delivery_person_info(
    delivery_person = Depends(get_current_delivery_person)
):
    """Get current delivery person information"""
    return ResponseModel(
        success=True,
        data={
            "id": delivery_person.id,
            "name": delivery_person.name,
            "phone": delivery_person.phone,
            "email": delivery_person.email,
            "employeeId": delivery_person.employee_id,
            "vehicleNumber": delivery_person.vehicle_number,
            "vehicleType": delivery_person.vehicle_type,
            "isAvailable": delivery_person.is_available,
            "is_available": delivery_person.is_available,  # snake_case alias
            "isOnline": delivery_person.is_online,
            "is_online": delivery_person.is_online,  # snake_case alias
            "currentLatitude": delivery_person.current_latitude,
            "currentLongitude": delivery_person.current_longitude
        },
        message="Delivery person information retrieved successfully"
    )


@router.put("/me", response_model=ResponseModel)
async def update_delivery_person_info(
    payload: DeliverySelfUpdate,
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """Allow delivery person to update own basic profile fields."""
    if payload.phone and payload.phone != delivery_person.phone:
        existing_phone = db.query(DeliveryPerson).filter(
            DeliveryPerson.phone == payload.phone,
            DeliveryPerson.id != delivery_person.id
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    if payload.email and payload.email != delivery_person.email:
        existing_email = db.query(DeliveryPerson).filter(
            DeliveryPerson.email == payload.email,
            DeliveryPerson.id != delivery_person.id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    if payload.name is not None:
        delivery_person.name = payload.name.strip()
    if payload.phone is not None:
        delivery_person.phone = payload.phone.strip()
    if payload.email is not None:
        delivery_person.email = payload.email.strip().lower()
    if payload.vehicleNumber is not None:
        delivery_person.vehicle_number = payload.vehicleNumber.strip()
    if payload.vehicleType is not None:
        delivery_person.vehicle_type = payload.vehicleType.strip()

    db.commit()
    db.refresh(delivery_person)

    return ResponseModel(
        success=True,
        data={
            "id": delivery_person.id,
            "name": delivery_person.name,
            "phone": delivery_person.phone,
            "email": delivery_person.email,
            "employeeId": delivery_person.employee_id,
            "employee_id": delivery_person.employee_id,
            "vehicleNumber": delivery_person.vehicle_number,
            "vehicle_number": delivery_person.vehicle_number,
            "vehicleType": delivery_person.vehicle_type,
            "vehicle_type": delivery_person.vehicle_type,
            "isAvailable": delivery_person.is_available,
            "is_available": delivery_person.is_available,
            "isOnline": delivery_person.is_online,
            "is_online": delivery_person.is_online,
            "currentLatitude": delivery_person.current_latitude,
            "currentLongitude": delivery_person.current_longitude
        },
        message="Profile updated successfully"
    )
