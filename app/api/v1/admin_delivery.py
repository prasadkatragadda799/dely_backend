"""
Admin Delivery Management Endpoints
For managing delivery personnel and assigning orders
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.delivery import DeliveryPersonCreate, DeliveryPersonUpdate, OrderAssignment
from app.models.delivery_person import DeliveryPerson
from app.models.order import Order
from app.models.admin import Admin
from app.api.admin_deps import require_manager_or_above
from app.utils.security import get_password_hash
from app.utils.admin_activity import log_admin_activity
import secrets

router = APIRouter()


@router.get("/persons", response_model=ResponseModel)
async def list_delivery_persons(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_available: Optional[bool] = None,
    is_online: Optional[bool] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """List all delivery persons with filters"""
    query = db.query(DeliveryPerson)
    
    # Apply filters
    if search:
        query = query.filter(
            (DeliveryPerson.name.ilike(f"%{search}%")) |
            (DeliveryPerson.phone.ilike(f"%{search}%")) |
            (DeliveryPerson.employee_id.ilike(f"%{search}%"))
        )
    
    if is_active is not None:
        query = query.filter(DeliveryPerson.is_active == is_active)
    
    if is_available is not None:
        query = query.filter(DeliveryPerson.is_available == is_available)
    
    if is_online is not None:
        query = query.filter(DeliveryPerson.is_online == is_online)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    delivery_persons = query.offset(offset).limit(limit).all()
    
    # Format response
    persons_list = []
    for dp in delivery_persons:
        # Count assigned orders
        active_orders = db.query(Order).filter(
            Order.delivery_person_id == dp.id,
            Order.status.in_(["confirmed", "processing", "shipped", "out_for_delivery"])
        ).count()
        
        persons_list.append({
            "id": dp.id,
            "name": dp.name,
            "phone": dp.phone,
            "email": dp.email,
            "employeeId": dp.employee_id,
            "employee_id": dp.employee_id,
            "vehicleNumber": dp.vehicle_number,
            "vehicle_number": dp.vehicle_number,
            "vehicleType": dp.vehicle_type,
            "vehicle_type": dp.vehicle_type,
            "isActive": dp.is_active,
            "is_active": dp.is_active,
            "isAvailable": dp.is_available,
            "is_available": dp.is_available,
            "isOnline": dp.is_online,
            "is_online": dp.is_online,
            "activeOrders": active_orders,
            "active_orders": active_orders,
            "lastLogin": dp.last_login.isoformat() if dp.last_login else None,
            "last_login": dp.last_login.isoformat() if dp.last_login else None,
            "createdAt": dp.created_at.isoformat() if dp.created_at else None,
            "created_at": dp.created_at.isoformat() if dp.created_at else None
        })
    
    return ResponseModel(
        success=True,
        data={
            "items": persons_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 0
            }
        },
        message="Delivery persons retrieved successfully"
    )


@router.post("/persons", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_delivery_person(
    person_data: DeliveryPersonCreate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Create a new delivery person"""
    # Check if phone already exists
    existing = db.query(DeliveryPerson).filter(
        DeliveryPerson.phone == person_data.phone
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Check if email already exists (if provided)
    if person_data.email:
        existing_email = db.query(DeliveryPerson).filter(
            DeliveryPerson.email == person_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Hash password
    password_hash = get_password_hash(person_data.password)
    
    # Create delivery person
    new_person = DeliveryPerson(
        name=person_data.name,
        phone=person_data.phone,
        email=person_data.email,
        password_hash=password_hash,
        employee_id=person_data.employeeId,
        license_number=person_data.licenseNumber,
        vehicle_number=person_data.vehicleNumber,
        vehicle_type=person_data.vehicleType,
        is_active=True
    )
    
    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="delivery_person_created",
        entity_type="delivery_person",
        entity_id=None,
        details={"name": new_person.name, "phone": new_person.phone},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "id": new_person.id,
            "name": new_person.name,
            "phone": new_person.phone,
            "employeeId": new_person.employee_id
        },
        message="Delivery person created successfully"
    )


@router.put("/persons/{person_id}", response_model=ResponseModel)
async def update_delivery_person(
    person_id: str,
    person_data: DeliveryPersonUpdate,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update delivery person details"""
    person = db.query(DeliveryPerson).filter(DeliveryPerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Delivery person not found")
    
    # Update fields
    if person_data.name is not None:
        person.name = person_data.name
    if person_data.email is not None:
        person.email = person_data.email
    if person_data.phone is not None:
        person.phone = person_data.phone
    if person_data.employeeId is not None:
        person.employee_id = person_data.employeeId
    if person_data.licenseNumber is not None:
        person.license_number = person_data.licenseNumber
    if person_data.vehicleNumber is not None:
        person.vehicle_number = person_data.vehicleNumber
    if person_data.vehicleType is not None:
        person.vehicle_type = person_data.vehicleType
    if person_data.isActive is not None:
        person.is_active = person_data.isActive
    if person_data.isAvailable is not None:
        person.is_available = person_data.isAvailable
    
    db.commit()
    
    return ResponseModel(
        success=True,
        message="Delivery person updated successfully"
    )


@router.post("/assign", response_model=ResponseModel)
async def assign_order_to_delivery(
    assignment: OrderAssignment,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Assign an order to a delivery person"""
    # Check if order exists
    order = db.query(Order).filter(Order.id == assignment.orderId).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if delivery person exists
    delivery_person = db.query(DeliveryPerson).filter(
        DeliveryPerson.id == assignment.deliveryPersonId
    ).first()
    if not delivery_person:
        raise HTTPException(status_code=404, detail="Delivery person not found")
    
    if not delivery_person.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery person is not active"
        )
    
    # Assign order
    order.delivery_person_id = delivery_person.id
    db.commit()
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="order_assigned_to_delivery",
        entity_type="order",
        entity_id=None,
        details={
            "order_id": order.id,
            "order_number": order.order_number,
            "delivery_person": delivery_person.name
        },
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={
            "orderId": order.id,
            "deliveryPerson": delivery_person.name
        },
        message=f"Order assigned to {delivery_person.name}"
    )


@router.get("/persons/{person_id}/orders", response_model=ResponseModel)
async def get_delivery_person_orders(
    person_id: str,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get all orders assigned to a delivery person"""
    person = db.query(DeliveryPerson).filter(DeliveryPerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Delivery person not found")
    
    orders = db.query(Order).filter(Order.delivery_person_id == person_id).all()
    
    orders_list = []
    for order in orders:
        orders_list.append({
            "id": order.id,
            "orderNumber": order.order_number,
            "order_number": order.order_number,
            "status": order.status.value,
            "totalAmount": float(order.total_amount),
            "total_amount": float(order.total_amount),
            "createdAt": order.created_at.isoformat() if order.created_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None
        })
    
    return ResponseModel(
        success=True,
        data={
            "deliveryPerson": person.name,
            "orders": orders_list,
            "total": len(orders_list)
        },
        message="Orders retrieved successfully"
    )
