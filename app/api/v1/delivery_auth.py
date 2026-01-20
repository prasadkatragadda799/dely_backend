"""
Delivery Person Authentication Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas.delivery import DeliveryLogin, DeliveryPersonResponse
from app.schemas.common import ResponseModel
from app.models.delivery_person import DeliveryPerson
from app.utils.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.config import settings

router = APIRouter()


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
    # Find delivery person by phone
    delivery_person = db.query(DeliveryPerson).filter(
        DeliveryPerson.phone == credentials.phone
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
    
    # Update last login and set online
    delivery_person.last_login = datetime.utcnow()
    delivery_person.is_online = True
    db.commit()
    
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
            "isOnline": delivery_person.is_online,
            "currentLatitude": delivery_person.current_latitude,
            "currentLongitude": delivery_person.current_longitude
        },
        message="Delivery person information retrieved successfully"
    )
