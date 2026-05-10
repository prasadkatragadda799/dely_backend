"""
Seller Analytics Endpoints
Returns data scoped to the authenticated seller's products.
Managers and above see platform-wide data.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct
from typing import Optional
from datetime import date, timedelta

from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.admin import Admin, AdminRole
from app.api.admin_deps import require_seller_or_above
from app.utils.analytics_helpers import (
    get_period_date_range,
    get_previous_period_date_range,
    calculate_percentage_change,
    format_period_label,
)

router = APIRouter()

_SELLER_ROLES = {AdminRole.SELLER}
_MANAGER_AND_ABOVE = {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MANAGER}


def _seller_product_filter(seller: Admin):
    """Return a SQLAlchemy filter expression scoping products to the seller when role is SELLER."""
    if seller.role in _SELLER_ROLES:
        return Product.created_by == str(seller.id)
    return None  # No filter — manager/admin sees all


@router.get("/dashboard", response_model=ResponseModel)
async def get_seller_dashboard(
    period: Optional[str] = Query("month", pattern="^(week|month|quarter|year|all)$"),
    dateFrom: Optional[date] = Query(None, alias="dateFrom"),
    dateTo: Optional[date] = Query(None, alias="dateTo"),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db),
):
    """
    Seller dashboard metrics.

    - SELLER role: revenue, orders and products scoped to their own products.
    - MANAGER / ADMIN / SUPER_ADMIN: platform-wide figures (same as admin analytics).
    """
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        prev_start_dt, prev_end_dt = get_previous_period_date_range(start_dt, end_dt)

        scope_filter = _seller_product_filter(seller)

        # ── Revenue (sum of order-item amounts, not order totals) ─────────────────
        def _revenue_query(start, end):
            q = (
                db.query(func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0))
                .join(Product, OrderItem.product_id == Product.id)
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    Order.created_at >= start,
                    Order.created_at <= end,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
            if scope_filter is not None:
                q = q.filter(scope_filter)
            return q.scalar() or 0.0

        total_revenue = _revenue_query(start_dt, end_dt)
        prev_revenue = _revenue_query(prev_start_dt, prev_end_dt)
        revenue_change = calculate_percentage_change(float(total_revenue), float(prev_revenue))

        # ── Orders (distinct orders that contain seller's products) ───────────────
        def _orders_query(start, end):
            q = (
                db.query(func.count(distinct(Order.id)))
                .join(OrderItem, Order.id == OrderItem.order_id)
                .join(Product, OrderItem.product_id == Product.id)
                .filter(
                    Order.created_at >= start,
                    Order.created_at <= end,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
            if scope_filter is not None:
                q = q.filter(scope_filter)
            return q.scalar() or 0

        total_orders = _orders_query(start_dt, end_dt)
        prev_orders = _orders_query(prev_start_dt, prev_end_dt)
        orders_change = calculate_percentage_change(float(total_orders), float(prev_orders))

        # ── Products ──────────────────────────────────────────────────────────────
        product_q = db.query(Product)
        if scope_filter is not None:
            product_q = product_q.filter(scope_filter)

        total_products = product_q.count()
        active_products = product_q.filter(Product.is_available == True).count()
        inactive_products = total_products - active_products

        # ── Average Order Value (by seller revenue share per order) ───────────────
        avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0.0
        prev_avg = float(prev_revenue / prev_orders) if prev_orders > 0 else 0.0
        avg_order_value_change = calculate_percentage_change(avg_order_value, prev_avg)

        # ── Top products ──────────────────────────────────────────────────────────
        top_q = (
            db.query(
                Product.id,
                Product.name,
                func.sum(OrderItem.quantity).label("sales"),
                func.sum(OrderItem.quantity * OrderItem.price).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        if scope_filter is not None:
            top_q = top_q.filter(scope_filter)

        top_products = (
            top_q.group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity * OrderItem.price).desc())
            .limit(5)
            .all()
        )

        top_products_data = [
            {
                "productId": str(row.id),
                "name": row.name,
                "sales": int(row.sales or 0),
                "revenue": round(float(row.revenue or 0), 2),
            }
            for row in top_products
        ]

        return ResponseModel(
            success=True,
            data={
                "totalRevenue": round(float(total_revenue), 2),
                "totalOrders": total_orders,
                "totalProducts": total_products,
                "activeProducts": active_products,
                "inactiveProducts": inactive_products,
                "avgOrderValue": round(avg_order_value, 2),
                "revenueChange": revenue_change,
                "ordersChange": orders_change,
                "avgOrderValueChange": avg_order_value_change,
                "topProducts": top_products_data,
                "scope": "seller" if seller.role in _SELLER_ROLES else "platform",
            },
            message="Seller dashboard metrics retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving seller dashboard: {str(e)}")


@router.get("/revenue", response_model=ResponseModel)
async def get_seller_revenue(
    period: Optional[str] = Query("month", pattern="^(week|month|quarter|year|all)$"),
    dateFrom: Optional[date] = Query(None, alias="dateFrom"),
    dateTo: Optional[date] = Query(None, alias="dateTo"),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db),
):
    """Revenue time-series scoped to the seller's products (single aggregated query per period type)."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        scope_filter = _seller_product_filter(seller)

        # Use daily truncation for week/month periods, monthly for quarter/year/all.
        # This gives us one DB round-trip instead of N (2×periods) round-trips.
        trunc_unit = "day" if period in ("week", "month") else "month"

        base_q = (
            db.query(
                func.date_trunc(trunc_unit, Order.created_at).label("bucket"),
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0.0).label("revenue"),
                func.count(distinct(Order.id)).label("orders"),
            )
            .select_from(OrderItem)
            .join(Product, OrderItem.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        if scope_filter is not None:
            base_q = base_q.filter(scope_filter)

        rows = base_q.group_by(func.date_trunc(trunc_unit, Order.created_at)).all()

        # Build lookup keyed by date (first day of the bucket)
        data_by_date: dict = {}
        for row in rows:
            bucket_date = row.bucket.date() if hasattr(row.bucket, "date") else row.bucket
            data_by_date[bucket_date] = {
                "revenue": float(row.revenue or 0),
                "orders": int(row.orders or 0),
            }

        def _lookup_day(dt) -> dict:
            key = dt.date() if hasattr(dt, "date") else dt
            return data_by_date.get(key, {"revenue": 0.0, "orders": 0})

        def _lookup_month(dt) -> dict:
            key = (dt.date() if hasattr(dt, "date") else dt).replace(day=1)
            return data_by_date.get(key, {"revenue": 0.0, "orders": 0})

        result = []

        if period == "week":
            for i in range(7):
                day_start = start_dt + timedelta(days=i)
                d = _lookup_day(day_start)
                result.append({
                    "period": format_period_label("week", day_start),
                    "name": format_period_label("week", day_start),
                    "revenue": round(d["revenue"], 2),
                    "orders": d["orders"],
                })

        elif period == "month":
            # Sum daily buckets across each 7-day window
            for i in range(4):
                week_start = start_dt + timedelta(days=i * 7)
                rev, ords = 0.0, 0
                for j in range(7):
                    day = week_start + timedelta(days=j)
                    if day <= end_dt:
                        d = _lookup_day(day)
                        rev += d["revenue"]
                        ords += d["orders"]
                result.append({
                    "period": format_period_label("month", week_start, i),
                    "name": format_period_label("month", week_start, i),
                    "revenue": round(rev, 2),
                    "orders": ords,
                })

        elif period in ("quarter", "year"):
            num_months = 3 if period == "quarter" else 12
            for i in range(num_months):
                month_start = (start_dt.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
                if month_start > end_dt:
                    break
                d = _lookup_month(month_start)
                result.append({
                    "period": format_period_label(period, month_start),
                    "name": format_period_label(period, month_start),
                    "revenue": round(d["revenue"], 2),
                    "orders": d["orders"],
                })

        else:  # all
            first_q = db.query(func.min(Order.created_at)).scalar()
            if not first_q:
                return ResponseModel(success=True, data=[], message="No order data available")
            current_month = first_q.replace(day=1)
            while current_month <= end_dt:
                d = _lookup_month(current_month)
                result.append({
                    "period": format_period_label("all", current_month),
                    "name": format_period_label("all", current_month),
                    "revenue": round(d["revenue"], 2),
                    "orders": d["orders"],
                })
                current_month = (
                    current_month.replace(year=current_month.year + 1, month=1, day=1)
                    if current_month.month == 12
                    else current_month.replace(month=current_month.month + 1, day=1)
                )

        return ResponseModel(
            success=True,
            data=result,
            message="Seller revenue analytics retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving seller revenue: {str(e)}")


@router.get("/products", response_model=ResponseModel)
async def get_seller_product_analytics(
    period: Optional[str] = Query("month", pattern="^(week|month|quarter|year|all)$"),
    dateFrom: Optional[date] = Query(None, alias="dateFrom"),
    dateTo: Optional[date] = Query(None, alias="dateTo"),
    limit: Optional[int] = Query(10, ge=1, le=100),
    seller: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db),
):
    """Top products by revenue, scoped to the seller's catalogue."""
    try:
        start_dt, end_dt = get_period_date_range(period, dateFrom, dateTo)
        scope_filter = _seller_product_filter(seller)

        q = (
            db.query(
                Product.id,
                Product.name,
                func.sum(OrderItem.quantity).label("sales"),
                func.sum(OrderItem.quantity * OrderItem.price).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        if scope_filter is not None:
            q = q.filter(scope_filter)

        rows = (
            q.group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity * OrderItem.price).desc())
            .limit(limit)
            .all()
        )

        result = [
            {
                "productId": str(row.id),
                "name": row.name,
                "sales": int(row.sales or 0),
                "revenue": round(float(row.revenue or 0), 2),
                "amount": round(float(row.revenue or 0), 2),
            }
            for row in rows
        ]

        return ResponseModel(
            success=True,
            data=result,
            message="Seller product analytics retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving seller product analytics: {str(e)}")
