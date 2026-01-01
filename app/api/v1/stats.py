from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.stats import QuickStatsResponse
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderStatus
from decimal import Decimal

router = APIRouter()


@router.get("/quick", response_model=ResponseModel)
def get_quick_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick statistics for user"""
    # Total orders
    total_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
    
    # Total spent
    total_spent_result = db.query(func.sum(Order.total)).filter(
        Order.user_id == current_user.id,
        Order.status != OrderStatus.CANCELLED
    ).scalar()
    total_spent = Decimal(str(total_spent_result)) if total_spent_result else Decimal('0.00')
    
    # Pending orders
    pending_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
    ).count()
    
    # Total savings (sum of discounts)
    total_discount_result = db.query(func.sum(Order.discount)).filter(
        Order.user_id == current_user.id,
        Order.status != OrderStatus.CANCELLED
    ).scalar()
    savings = Decimal(str(total_discount_result)) if total_discount_result else Decimal('0.00')
    
    return ResponseModel(
        success=True,
        data=QuickStatsResponse(
            total_orders=total_orders,
            total_spent=total_spent,
            pending_orders=pending_orders,
            savings=savings
        )
    )

