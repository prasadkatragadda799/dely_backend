"""
Admin Analytics Endpoints
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from typing import Optional
from datetime import datetime, date, timedelta
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderStatus
from app.models.user import User, KYCStatus
from app.models.product import Product
from app.models.kyc import KYC
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.models.admin import Admin

router = APIRouter()


@router.get("/dashboard", response_model=ResponseModel)
async def get_dashboard_stats(
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    week_start = today_start - timedelta(days=now.weekday())
    month_start = datetime(now.year, now.month, 1)
    
    # Revenue calculations
    revenue_today = db.query(func.sum(Order.total_amount)).filter(
        and_(
            Order.created_at >= today_start,
            Order.status == OrderStatus.DELIVERED
        )
    ).scalar() or 0.0
    
    revenue_week = db.query(func.sum(Order.total_amount)).filter(
        and_(
            Order.created_at >= week_start,
            Order.status == OrderStatus.DELIVERED
        )
    ).scalar() or 0.0
    
    revenue_month = db.query(func.sum(Order.total_amount)).filter(
        and_(
            Order.created_at >= month_start,
            Order.status == OrderStatus.DELIVERED
        )
    ).scalar() or 0.0
    
    revenue_all_time = db.query(func.sum(Order.total_amount)).filter(
        Order.status == OrderStatus.DELIVERED
    ).scalar() or 0.0
    
    # Calculate revenue change (this month vs last month)
    last_month_start = datetime(now.year, now.month - 1, 1) if now.month > 1 else datetime(now.year - 1, 12, 1)
    last_month_end = month_start - timedelta(days=1)
    revenue_last_month = db.query(func.sum(Order.total_amount)).filter(
        and_(
            Order.created_at >= last_month_start,
            Order.created_at <= last_month_end,
            Order.status == OrderStatus.DELIVERED
        )
    ).scalar() or 0.0
    
    revenue_change = 0.0
    if revenue_last_month > 0:
        revenue_change = ((revenue_month - revenue_last_month) / revenue_last_month) * 100
    
    # Orders statistics
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.PENDING
    ).scalar() or 0
    confirmed_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.CONFIRMED
    ).scalar() or 0
    shipped_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.SHIPPED
    ).scalar() or 0
    delivered_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.DELIVERED
    ).scalar() or 0
    cancelled_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.CANCELLED
    ).scalar() or 0
    
    # Calculate order change (this month vs last month)
    orders_this_month = db.query(func.count(Order.id)).filter(
        Order.created_at >= month_start
    ).scalar() or 0
    orders_last_month = db.query(func.count(Order.id)).filter(
        and_(
            Order.created_at >= last_month_start,
            Order.created_at <= last_month_end
        )
    ).scalar() or 0
    
    order_change = 0.0
    if orders_last_month > 0:
        order_change = ((orders_this_month - orders_last_month) / orders_last_month) * 100
    
    # Users statistics
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_30_days = db.query(func.count(User.id)).filter(
        User.created_at >= (now - timedelta(days=30))
    ).scalar() or 0
    
    # Users active in last 30 days (users who placed orders)
    active_users_30_days = db.query(func.count(func.distinct(Order.user_id))).filter(
        Order.created_at >= (now - timedelta(days=30))
    ).scalar() or 0
    
    new_users_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar() or 0
    
    # Calculate user change
    users_this_month = db.query(func.count(User.id)).filter(
        User.created_at >= month_start
    ).scalar() or 0
    users_last_month = db.query(func.count(User.id)).filter(
        and_(
            User.created_at >= last_month_start,
            User.created_at <= last_month_end
        )
    ).scalar() or 0
    
    user_change = 0.0
    if users_last_month > 0:
        user_change = ((users_this_month - users_last_month) / users_last_month) * 100
    
    # Products statistics
    total_products = db.query(func.count(Product.id)).scalar() or 0
    in_stock = db.query(func.count(Product.id)).filter(
        and_(
            Product.stock_quantity > 10,
            Product.is_available == True
        )
    ).scalar() or 0
    low_stock = db.query(func.count(Product.id)).filter(
        and_(
            Product.stock_quantity > 0,
            Product.stock_quantity <= 10,
            Product.is_available == True
        )
    ).scalar() or 0
    out_of_stock = db.query(func.count(Product.id)).filter(
        Product.stock_quantity == 0
    ).scalar() or 0
    
    # KYC pending
    kyc_pending = db.query(func.count(User.id)).filter(
        User.kyc_status == KYCStatus.PENDING
    ).scalar() or 0
    
    # Average order value
    avg_order_value = 0.0
    if delivered_orders > 0:
        avg_order_value = float(revenue_all_time) / delivered_orders
    
    # Conversion rate (orders / users)
    conversion_rate = 0.0
    if total_users > 0:
        conversion_rate = (total_orders / total_users) * 100
    
    dashboard_data = {
        "revenue": {
            "today": float(revenue_today),
            "thisWeek": float(revenue_week),
            "thisMonth": float(revenue_month),
            "allTime": float(revenue_all_time),
            "change": round(revenue_change, 2)
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "confirmed": confirmed_orders,
            "shipped": shipped_orders,
            "delivered": delivered_orders,
            "cancelled": cancelled_orders,
            "change": round(order_change, 2)
        },
        "users": {
            "total": total_users,
            "active30Days": active_users_30_days,
            "newToday": new_users_today,
            "change": round(user_change, 2)
        },
        "products": {
            "total": total_products,
            "inStock": in_stock,
            "lowStock": low_stock,
            "outOfStock": out_of_stock
        },
        "kycPending": kyc_pending,
        "averageOrderValue": round(avg_order_value, 2),
        "conversionRate": round(conversion_rate, 2)
    }
    
    return ResponseModel(
        success=True,
        data=dashboard_data,
        message="Dashboard statistics retrieved successfully"
    )


@router.get("/revenue", response_model=ResponseModel)
async def get_revenue_analytics(
    period: str = Query("monthly", pattern="^(daily|weekly|monthly|yearly)$"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get revenue analytics"""
    query = db.query(Order).filter(
        Order.status == OrderStatus.DELIVERED
    )
    
    # Apply date filters
    if date_from:
        query = query.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
    
    # Group by period
    if period == "daily":
        revenue_data = db.query(
            func.date(Order.created_at).label('period'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).filter(
            Order.status == OrderStatus.DELIVERED
        )
        if date_from:
            revenue_data = revenue_data.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            revenue_data = revenue_data.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        revenue_data = revenue_data.group_by(func.date(Order.created_at)).all()
        
        result = [{
            "period": str(row.period),
            "revenue": float(row.revenue or 0),
            "orders": row.orders
        } for row in revenue_data]
        
    elif period == "weekly":
        revenue_data = db.query(
            func.strftime('%Y-W%W', Order.created_at).label('period'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).filter(
            Order.status == OrderStatus.DELIVERED
        )
        if date_from:
            revenue_data = revenue_data.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            revenue_data = revenue_data.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        revenue_data = revenue_data.group_by(func.strftime('%Y-W%W', Order.created_at)).all()
        
        result = [{
            "period": row.period,
            "revenue": float(row.revenue or 0),
            "orders": row.orders
        } for row in revenue_data]
        
    elif period == "monthly":
        revenue_data = db.query(
            func.strftime('%Y-%m', Order.created_at).label('period'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).filter(
            Order.status == OrderStatus.DELIVERED
        )
        if date_from:
            revenue_data = revenue_data.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            revenue_data = revenue_data.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        revenue_data = revenue_data.group_by(func.strftime('%Y-%m', Order.created_at)).all()
        
        result = [{
            "period": row.period,
            "revenue": float(row.revenue or 0),
            "orders": row.orders
        } for row in revenue_data]
        
    else:  # yearly
        revenue_data = db.query(
            func.strftime('%Y', Order.created_at).label('period'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).filter(
            Order.status == OrderStatus.DELIVERED
        )
        if date_from:
            revenue_data = revenue_data.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            revenue_data = revenue_data.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        revenue_data = revenue_data.group_by(func.strftime('%Y', Order.created_at)).all()
        
        result = [{
            "period": row.period,
            "revenue": float(row.revenue or 0),
            "orders": row.orders
        } for row in revenue_data]
    
    return ResponseModel(
        success=True,
        data=result,
        message="Revenue analytics retrieved successfully"
    )

