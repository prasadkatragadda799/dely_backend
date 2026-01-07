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


@router.get("", response_model=ResponseModel)
@router.get("/quick", response_model=ResponseModel)
def get_quick_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick statistics for user with both snake_case and camelCase fields"""
    # Total orders
    total_orders = db.query(Order).filter(Order.user_id == str(current_user.id)).count()
    
    # Total spent (use total_amount, fallback to total for backward compatibility)
    total_spent_result = db.query(func.sum(Order.total_amount)).filter(
        Order.user_id == str(current_user.id),
        Order.status != OrderStatus.CANCELLED
    ).scalar()
    if not total_spent_result:
        # Fallback to total field if total_amount is null
        total_spent_result = db.query(func.sum(Order.total)).filter(
            Order.user_id == str(current_user.id),
            Order.status != OrderStatus.CANCELLED
        ).scalar()
    total_spent = Decimal(str(total_spent_result)) if total_spent_result else Decimal('0.00')
    
    # Total savings (sum of discounts from all orders)
    total_savings_result = db.query(func.sum(Order.discount)).filter(
        Order.user_id == str(current_user.id),
        Order.status != OrderStatus.CANCELLED
    ).scalar()
    total_savings = Decimal(str(total_savings_result)) if total_savings_result else Decimal('0.00')
    
    # Pending orders
    pending_orders = db.query(Order).filter(
        Order.user_id == str(current_user.id),
        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
    ).count()
    
    # Completed orders
    completed_orders = db.query(Order).filter(
        Order.user_id == str(current_user.id),
        Order.status == OrderStatus.DELIVERED
    ).count()
    
    # Build response with both snake_case and camelCase fields
    stats_data = {
        "total_orders": total_orders,
        "totalOrders": total_orders,  # camelCase alternative
        "order_count": total_orders,  # Alternative field name
        "total_spent": float(total_spent),
        "totalSpent": float(total_spent),  # camelCase alternative
        "total_amount": float(total_spent),  # Alternative field name
        "total_savings": float(total_savings),
        "totalSavings": float(total_savings),  # camelCase alternative
        "savings": float(total_savings),  # Alternative field name
        "pending_orders": pending_orders,
        "completed_orders": completed_orders
    }
    
    return ResponseModel(
        success=True,
        data=stats_data,
        message="Stats fetched successfully"
    )

