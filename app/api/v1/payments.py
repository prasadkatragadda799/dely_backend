from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.payment import PaymentInitiate, PaymentInitiateResponse, PaymentVerify, PaymentVerifyResponse
from app.schemas.common import ResponseModel
from app.models.order import Order
from uuid import UUID
import secrets

router = APIRouter()


@router.post("/initiate", response_model=ResponseModel)
def initiate_payment(
    payment_data: PaymentInitiate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate payment"""
    order = db.query(Order).filter(
        Order.id == payment_data.order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status.value != "pending":
        raise HTTPException(status_code=400, detail="Order cannot be paid")
    
    # Generate payment ID
    payment_id = f"PAY{secrets.token_hex(8).upper()}"
    
    # In production, integrate with Razorpay/Paytm
    # For now, return mock response
    payment_url = None
    if payment_data.payment_method.lower() == "online":
        payment_url = f"https://payment-gateway.com/pay/{payment_id}"
    
    # Update order payment details
    payment_details = payment_data.payment_details or {}
    order.payment_details = {
        "payment_id": payment_id,
        "payment_method": payment_data.payment_method,
        **payment_details
    }
    db.commit()
    
    return ResponseModel(
        success=True,
        data=PaymentInitiateResponse(
            payment_id=payment_id,
            payment_url=payment_url,
            status="initiated"
        )
    )


@router.post("/verify", response_model=ResponseModel)
def verify_payment(
    payment_data: PaymentVerify,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify payment"""
    # In production, verify with payment gateway
    # For now, mock verification
    
    # Find order by payment_id in payment_details
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).all()
    
    order = None
    for o in orders:
        if o.payment_details and o.payment_details.get("payment_id") == payment_data.payment_id:
            order = o
            break
    
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Mock verification - in production, call payment gateway API
    payment_status = "success"  # or "failed"
    
    if payment_status == "success":
        from app.models.order import OrderStatus
        order.status = OrderStatus.CONFIRMED
        db.commit()
    
    return ResponseModel(
        success=True,
        data=PaymentVerifyResponse(
            payment_status=payment_status,
            order_id=order.id
        )
    )

