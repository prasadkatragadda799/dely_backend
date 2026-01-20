"""
Admin Analytics Endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, distinct
from typing import Optional
from datetime import datetime, date, timedelta
import io
import csv

from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.company import Company
from app.api.admin_deps import require_manager_or_above
from app.models.admin import Admin
from app.utils.analytics_helpers import (
    get_period_date_range,
    get_previous_period_date_range,
    calculate_percentage_change,
    format_period_label,
    get_active_users_threshold,
    get_status_color,
    get_payment_method_color
)

router = APIRouter()


@router.get("/dashboard", response_model=ResponseModel)
async def get_dashboard_metrics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics with period-over-period comparison.
    
    Query Parameters:
    - period: week | month | quarter | year | all (default: month)
    - dateFrom: ISO date string (YYYY-MM-DD) - optional
    - dateTo: ISO date string (YYYY-MM-DD) - optional
    """
    try:
        # Get date ranges
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        prev_start_dt, prev_end_dt = get_previous_period_date_range(start_dt, end_dt)
        
        # Total Revenue (current period)
        total_revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED
            )
        ).scalar() or 0.0
        
        # Previous period revenue
        prev_revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            and_(
                Order.created_at >= prev_start_dt,
                Order.created_at <= prev_end_dt,
                Order.status != OrderStatus.CANCELLED
            )
        ).scalar() or 0.0
        
        revenue_change = calculate_percentage_change(float(total_revenue), float(prev_revenue))
        
        # Total Orders (current period)
        total_orders = db.query(func.count(Order.id)).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt
            )
        ).scalar() or 0
        
        # Previous period orders
        prev_orders = db.query(func.count(Order.id)).filter(
            and_(
                Order.created_at >= prev_start_dt,
                Order.created_at <= prev_end_dt
            )
        ).scalar() or 0
        
        orders_change = calculate_percentage_change(float(total_orders), float(prev_orders))
        
        # Active Users (users with activity in last 7 days)
        active_threshold = get_active_users_threshold()
        active_users = db.query(func.count(User.id)).filter(
            and_(
                User.last_active_at >= active_threshold,
                User.is_active == True
            )
        ).scalar() or 0
        
        # Previous period active users (7 days before that)
        prev_active_threshold = active_threshold - timedelta(days=7)
        prev_active_users = db.query(func.count(User.id)).filter(
            and_(
                User.last_active_at >= prev_active_threshold,
                User.last_active_at < active_threshold,
                User.is_active == True
            )
        ).scalar() or 0
        
        users_change = calculate_percentage_change(float(active_users), float(prev_active_users))
        
        # Average Order Value
        avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0.0
        prev_avg_order_value = float(prev_revenue / prev_orders) if prev_orders > 0 else 0.0
        avg_order_value_change = calculate_percentage_change(avg_order_value, prev_avg_order_value)
        
        dashboard_data = {
            "totalRevenue": round(float(total_revenue), 2),
            "totalOrders": total_orders,
            "activeUsers": active_users,
            "avgOrderValue": round(avg_order_value, 2),
            "revenueChange": revenue_change,
            "ordersChange": orders_change,
            "usersChange": users_change,
            "avgOrderValueChange": avg_order_value_change
        }
        
        return ResponseModel(
            success=True,
            data=dashboard_data,
            message="Dashboard metrics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard metrics: {str(e)}")


@router.get("/revenue", response_model=ResponseModel)
async def get_revenue_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """
    Get revenue analytics time-series data.
    
    Returns daily/weekly/monthly data based on period.
    """
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        result = []
        
        if period == 'week':
            # Daily data for last 7 days
            for i in range(7):
                day_start = start_dt + timedelta(days=i)
                day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
                
                revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                    and_(
                        Order.created_at >= day_start,
                        Order.created_at <= day_end,
                        Order.status != OrderStatus.CANCELLED
                    )
                ).scalar() or 0.0
                
                orders = db.query(func.count(Order.id)).filter(
                    and_(
                        Order.created_at >= day_start,
                        Order.created_at <= day_end
                    )
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('week', day_start),
                    "revenue": round(float(revenue), 2),
                    "orders": orders
                })
        
        elif period == 'month':
            # Weekly data for last 4 weeks
            weeks = 4
            days_per_week = 7
            for i in range(weeks):
                week_start = start_dt + timedelta(days=i * days_per_week)
                week_end = week_start + timedelta(days=days_per_week) - timedelta(seconds=1)
                if week_end > end_dt:
                    week_end = end_dt
                
                revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                    and_(
                        Order.created_at >= week_start,
                        Order.created_at <= week_end,
                        Order.status != OrderStatus.CANCELLED
                    )
                ).scalar() or 0.0
                
                orders = db.query(func.count(Order.id)).filter(
                    and_(
                        Order.created_at >= week_start,
                        Order.created_at <= week_end
                    )
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('month', week_start, i),
                    "revenue": round(float(revenue), 2),
                    "orders": orders
                })
        
        elif period == 'quarter':
            # Monthly data for last 3 months
            for i in range(3):
                month_start = start_dt.replace(day=1) + timedelta(days=32 * i)
                month_start = month_start.replace(day=1)
                
                # Get last day of month
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)
                
                if month_end > end_dt:
                    month_end = end_dt
                
                revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                    and_(
                        Order.created_at >= month_start,
                        Order.created_at <= month_end,
                        Order.status != OrderStatus.CANCELLED
                    )
                ).scalar() or 0.0
                
                orders = db.query(func.count(Order.id)).filter(
                    and_(
                        Order.created_at >= month_start,
                        Order.created_at <= month_end
                    )
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('quarter', month_start),
                    "revenue": round(float(revenue), 2),
                    "orders": orders
                })
        
        elif period == 'year':
            # Monthly data for last 12 months
            for i in range(12):
                month_start = start_dt.replace(day=1) + timedelta(days=32 * i)
                month_start = month_start.replace(day=1)
                
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)
                
                if month_end > end_dt:
                    month_end = end_dt
                
                revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                    and_(
                        Order.created_at >= month_start,
                        Order.created_at <= month_end,
                        Order.status != OrderStatus.CANCELLED
                    )
                ).scalar() or 0.0
                
                orders = db.query(func.count(Order.id)).filter(
                    and_(
                        Order.created_at >= month_start,
                        Order.created_at <= month_end
                    )
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('year', month_start),
                    "revenue": round(float(revenue), 2),
                    "orders": orders
                })
        
        else:  # 'all'
            # Monthly data for all time
            # Get first order date
            first_order = db.query(func.min(Order.created_at)).scalar()
            if not first_order:
                return ResponseModel(success=True, data=[], message="No order data available")
            
            current_month = first_order.replace(day=1)
            while current_month <= end_dt:
                if current_month.month == 12:
                    month_end = current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(seconds=1)
                else:
                    month_end = current_month.replace(month=current_month.month + 1, day=1) - timedelta(seconds=1)
                
                if month_end > end_dt:
                    month_end = end_dt
                
                revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                    and_(
                        Order.created_at >= current_month,
                        Order.created_at <= month_end,
                        Order.status != OrderStatus.CANCELLED
                    )
                ).scalar() or 0.0
                
                orders = db.query(func.count(Order.id)).filter(
                    and_(
                        Order.created_at >= current_month,
                        Order.created_at <= month_end
                    )
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('all', current_month),
                    "revenue": round(float(revenue), 2),
                    "orders": orders
                })
                
                # Move to next month
                if current_month.month == 12:
                    current_month = current_month.replace(year=current_month.year + 1, month=1, day=1)
                else:
                    current_month = current_month.replace(month=current_month.month + 1, day=1)
        
        return ResponseModel(
            success=True,
            data=result,
            message="Revenue analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving revenue analytics: {str(e)}")


@router.get("/products", response_model=ResponseModel)
async def get_product_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    limit: Optional[int] = Query(10, ge=1, le=100),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get top products by revenue and sales."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        # Query top products
        product_analytics = db.query(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label('sales'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(
            OrderItem, Product.id == OrderItem.product_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Product.id, Product.name
        ).order_by(
            func.sum(OrderItem.quantity * OrderItem.price).desc()
        ).limit(limit).all()
        
        result = [{
            "name": row.name,
            "sales": int(row.sales or 0),
            "revenue": round(float(row.revenue or 0), 2),
            "productId": str(row.id)
        } for row in product_analytics]
        
        return ResponseModel(
            success=True,
            data=result,
            message="Product analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product analytics: {str(e)}")


@router.get("/categories", response_model=ResponseModel)
async def get_category_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get category performance analytics."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        # Query category analytics
        category_analytics = db.query(
            Category.id,
            Category.name,
            func.sum(OrderItem.quantity).label('sales'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(
            Product, Category.id == Product.category_id
        ).join(
            OrderItem, Product.id == OrderItem.product_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Category.id, Category.name
        ).order_by(
            func.sum(OrderItem.quantity * OrderItem.price).desc()
        ).all()
        
        result = [{
            "name": row.name,
            "sales": int(row.sales or 0),
            "revenue": round(float(row.revenue or 0), 2),
            "categoryId": str(row.id)
        } for row in category_analytics]
        
        return ResponseModel(
            success=True,
            data=result,
            message="Category analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving category analytics: {str(e)}")


@router.get("/companies", response_model=ResponseModel)
async def get_company_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get company performance analytics."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        # Query company analytics
        company_analytics = db.query(
            Company.id,
            Company.name,
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue'),
            func.count(distinct(Order.id)).label('orders')
        ).join(
            Product, Company.id == Product.company_id
        ).join(
            OrderItem, Product.id == OrderItem.product_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Company.id, Company.name
        ).order_by(
            func.sum(OrderItem.quantity * OrderItem.price).desc()
        ).all()
        
        result = [{
            "name": row.name,
            "revenue": round(float(row.revenue or 0), 2),
            "orders": int(row.orders or 0),
            "companyId": str(row.id)
        } for row in company_analytics]
        
        return ResponseModel(
            success=True,
            data=result,
            message="Company analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving company analytics: {str(e)}")


@router.get("/users", response_model=ResponseModel)
async def get_user_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get user growth analytics."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        result = []
        
        if period == 'week':
            # Daily data for last 7 days
            for i in range(7):
                day_start = start_dt + timedelta(days=i)
                day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
                
                # New users registered this day
                new_users = db.query(func.count(User.id)).filter(
                    and_(
                        User.created_at >= day_start,
                        User.created_at <= day_end
                    )
                ).scalar() or 0
                
                # Total users up to this day
                total_users = db.query(func.count(User.id)).filter(
                    User.created_at <= day_end
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('week', day_start),
                    "users": total_users,
                    "newUsers": new_users
                })
        
        elif period == 'month':
            # Weekly data for last 4 weeks
            weeks = 4
            days_per_week = 7
            for i in range(weeks):
                week_start = start_dt + timedelta(days=i * days_per_week)
                week_end = week_start + timedelta(days=days_per_week) - timedelta(seconds=1)
                if week_end > end_dt:
                    week_end = end_dt
                
                new_users = db.query(func.count(User.id)).filter(
                    and_(
                        User.created_at >= week_start,
                        User.created_at <= week_end
                    )
                ).scalar() or 0
                
                total_users = db.query(func.count(User.id)).filter(
                    User.created_at <= week_end
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('month', week_start, i),
                    "users": total_users,
                    "newUsers": new_users
                })
        
        elif period == 'quarter' or period == 'year':
            # Monthly data
            months = 3 if period == 'quarter' else 12
            for i in range(months):
                month_start = start_dt.replace(day=1) + timedelta(days=32 * i)
                month_start = month_start.replace(day=1)
                
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)
                
                if month_end > end_dt:
                    month_end = end_dt
                
                new_users = db.query(func.count(User.id)).filter(
                    and_(
                        User.created_at >= month_start,
                        User.created_at <= month_end
                    )
                ).scalar() or 0
                
                total_users = db.query(func.count(User.id)).filter(
                    User.created_at <= month_end
                ).scalar() or 0
                
                label_period = 'quarter' if period == 'quarter' else 'year'
                result.append({
                    "period": format_period_label(label_period, month_start),
                    "users": total_users,
                    "newUsers": new_users
                })
        
        else:  # 'all'
            # Monthly data for all time
            first_user = db.query(func.min(User.created_at)).scalar()
            if not first_user:
                return ResponseModel(success=True, data=[], message="No user data available")
            
            current_month = first_user.replace(day=1)
            while current_month <= end_dt:
                if current_month.month == 12:
                    month_end = current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(seconds=1)
                else:
                    month_end = current_month.replace(month=current_month.month + 1, day=1) - timedelta(seconds=1)
                
                if month_end > end_dt:
                    month_end = end_dt
                
                new_users = db.query(func.count(User.id)).filter(
                    and_(
                        User.created_at >= current_month,
                        User.created_at <= month_end
                    )
                ).scalar() or 0
                
                total_users = db.query(func.count(User.id)).filter(
                    User.created_at <= month_end
                ).scalar() or 0
                
                result.append({
                    "period": format_period_label('all', current_month),
                    "users": total_users,
                    "newUsers": new_users
                })
                
                # Move to next month
                if current_month.month == 12:
                    current_month = current_month.replace(year=current_month.year + 1, month=1, day=1)
                else:
                    current_month = current_month.replace(month=current_month.month + 1, day=1)
        
        return ResponseModel(
            success=True,
            data=result,
            message="User analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user analytics: {str(e)}")


@router.get("/orders", response_model=ResponseModel)
async def get_order_analytics(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Get order status and payment method distribution."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        # Order status distribution
        status_data = db.query(
            Order.status,
            func.count(Order.id).label('count')
        ).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt
            )
        ).group_by(Order.status).all()
        
        status_distribution = [{
            "name": row.status.value.capitalize() if hasattr(row.status, 'value') else str(row.status).capitalize(),
            "value": int(row.count),
            "color": get_status_color(row.status.value if hasattr(row.status, 'value') else str(row.status))
        } for row in status_data]
        
        # Payment method distribution
        payment_data = db.query(
            Order.payment_method,
            func.count(Order.id).label('count')
        ).filter(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.payment_method.isnot(None)
            )
        ).group_by(Order.payment_method).all()
        
        payment_method_distribution = [{
            "name": str(row.payment_method).replace('_', ' ').title() if row.payment_method else "Unknown",
            "value": int(row.count),
            "color": get_payment_method_color(str(row.payment_method) if row.payment_method else "unknown")
        } for row in payment_data]
        
        analytics_data = {
            "statusDistribution": status_distribution,
            "paymentMethodDistribution": payment_method_distribution
        }
        
        return ResponseModel(
            success=True,
            data=analytics_data,
            message="Order analytics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving order analytics: {str(e)}")


@router.get("/export", response_model=None)
async def export_analytics_report(
    period: Optional[str] = Query('month', pattern='^(week|month|quarter|year|all)$'),
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    format: Optional[str] = Query('csv', pattern='^(xlsx|csv)$'),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Export analytics report as CSV or XLSX."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        
        # For now, implement CSV export (XLSX requires openpyxl library)
        if format == 'csv':
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Dashboard metrics section
            writer.writerow(['DASHBOARD METRICS'])
            writer.writerow(['Metric', 'Value'])
            
            total_revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                and_(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    Order.status != OrderStatus.CANCELLED
                )
            ).scalar() or 0.0
            
            total_orders = db.query(func.count(Order.id)).filter(
                and_(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt
                )
            ).scalar() or 0
            
            active_users = db.query(func.count(User.id)).filter(
                and_(
                    User.last_active_at >= get_active_users_threshold(),
                    User.is_active == True
                )
            ).scalar() or 0
            
            avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0.0
            
            writer.writerow(['Total Revenue', f'₹{round(float(total_revenue), 2)}'])
            writer.writerow(['Total Orders', total_orders])
            writer.writerow(['Active Users', active_users])
            writer.writerow(['Average Order Value', f'₹{round(avg_order_value, 2)}'])
            writer.writerow([])
            
            # Top products section
            writer.writerow(['TOP PRODUCTS'])
            writer.writerow(['Product Name', 'Sales', 'Revenue'])
            
            product_analytics = db.query(
                Product.name,
                func.sum(OrderItem.quantity).label('sales'),
                func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                and_(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    Order.status != OrderStatus.CANCELLED
                )
            ).group_by(Product.name).order_by(
                func.sum(OrderItem.quantity * OrderItem.price).desc()
            ).limit(10).all()
            
            for row in product_analytics:
                writer.writerow([row.name, int(row.sales or 0), f'₹{round(float(row.revenue or 0), 2)}'])
            
            writer.writerow([])
            
            # Order status distribution
            writer.writerow(['ORDER STATUS DISTRIBUTION'])
            writer.writerow(['Status', 'Count'])
            
            status_data = db.query(
                Order.status,
                func.count(Order.id).label('count')
            ).filter(
                and_(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt
                )
            ).group_by(Order.status).all()
            
            for row in status_data:
                status_name = row.status.value.capitalize() if hasattr(row.status, 'value') else str(row.status).capitalize()
                writer.writerow([status_name, int(row.count)])
            
            # Get CSV content
            output.seek(0)
            csv_content = output.getvalue()
            
            # Create filename
            filename = f"analytics-report-{start_dt.strftime('%Y-%m-%d')}-to-{end_dt.strftime('%Y-%m-%d')}.csv"
            
            # Return as downloadable file
            return StreamingResponse(
                io.BytesIO(csv_content.encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        else:
            # XLSX format requires openpyxl library
            raise HTTPException(status_code=400, detail="XLSX format not yet implemented. Please use CSV format.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting analytics report: {str(e)}")
