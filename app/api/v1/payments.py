from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
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
    user_id_str = str(current_user.id)
    order_id_str = str(payment_data.order_id)

    order = db.query(Order).filter(
        Order.id == order_id_str,
        Order.user_id == user_id_str
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Be defensive: `order.status` may be an enum or a raw string depending on DB/migrations.
    order_status = getattr(order, "status", None)
    order_status_value = (
        order_status.value if hasattr(order_status, "value") else str(order_status)
    ).lower().strip()

    if order_status_value != "pending":
        raise HTTPException(status_code=400, detail="Order cannot be paid")
    
    # Generate payment ID
    payment_id = f"PAY{secrets.token_hex(8).upper()}"
    
    # In production, integrate with Razorpay/Paytm
    # For now, return mock response
    payment_url = None
    payment_method_normalized = (payment_data.payment_method or "").lower().strip()
    if not payment_method_normalized:
        raise HTTPException(status_code=400, detail="payment_method is required")

    if payment_method_normalized == "online":
        payment_url = f"https://payment-gateway.com/pay/{payment_id}"
    
    # Update order payment details
    payment_details = payment_data.payment_details or {}
    if not isinstance(payment_details, dict):
        payment_details = {}
    order.payment_details = {
        "payment_id": payment_id,
        "payment_method": payment_method_normalized,
        **payment_details
    }
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to initiate payment: {str(exc)}")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initiate payment: {str(exc)}")
    
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
    
    user_id_str = str(current_user.id)

    # Find order by payment_id in payment_details
    orders = db.query(Order).filter(
        Order.user_id == user_id_str
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
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Failed to verify payment: {str(exc)}")
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to verify payment: {str(exc)}")
    
    return ResponseModel(
        success=True,
        data=PaymentVerifyResponse(
            payment_status=payment_status,
            order_id=order.id
        )
    )

