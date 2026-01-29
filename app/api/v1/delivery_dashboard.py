"""
Delivery Dashboard Endpoint
Separate router for dashboard summary at /delivery/dashboard-summary
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderStatus
from app.models.delivery_person import DeliveryPerson
from app.api.v1.delivery_auth import get_current_delivery_person
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/dashboard-summary", response_model=ResponseModel)
async def get_dashboard_summary(
    delivery_person: DeliveryPerson = Depends(get_current_delivery_person),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary for delivery person.
    Returns today's earnings, completed orders, active order, and upcoming orders.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start
    
    # Get today's delivered orders
    today_delivered = db.query(Order).filter(
        Order.delivery_person_id == delivery_person.id,
        Order.status == OrderStatus.DELIVERED,
        Order.updated_at >= today_start,
        Order.updated_at < today_end
    ).all()
    
    # Calculate today's earnings (sum of total_amount for delivered orders)
    today_earnings = sum(
        float(order.total_amount) if order.total_amount else float(order.total)
        for order in today_delivered
    )
    
    # Get yesterday's delivered orders for comparison
    yesterday_delivered = db.query(Order).filter(
        Order.delivery_person_id == delivery_person.id,
        Order.status == OrderStatus.DELIVERED,
        Order.updated_at >= yesterday_start,
        Order.updated_at < yesterday_end
    ).all()
    
    yesterday_earnings = sum(
        float(order.total_amount) if order.total_amount else float(order.total)
        for order in yesterday_delivered
    )
    
    # Calculate earnings change percent
    earnings_change_percent = 0.0
    if yesterday_earnings > 0:
        earnings_change_percent = ((today_earnings - yesterday_earnings) / yesterday_earnings) * 100
    elif today_earnings > 0:
        earnings_change_percent = 100.0  # 100% increase if no earnings yesterday
    
    # Get active order (SHIPPED or OUT_FOR_DELIVERY)
    active_order = db.query(Order).options(
        joinedload(Order.order_items).joinedload("product")
    ).filter(
        Order.delivery_person_id == delivery_person.id,
        Order.status.in_([OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY])
    ).order_by(Order.created_at.desc()).first()
    
    # Get upcoming orders (CONFIRMED, PROCESSING - assigned but not yet picked up)
    upcoming_orders = db.query(Order).options(
        joinedload(Order.order_items).joinedload("product")
    ).filter(
        Order.delivery_person_id == delivery_person.id,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
    ).order_by(Order.created_at.asc()).all()
    
    # Helper to format order
    def _format_order(order: Order) -> dict:
        delivery_address = order.delivery_address or {}
        
        # Extract store/company name from first product's company (if available)
        store_name = "Warehouse"  # Default
        if order.order_items:
            first_item = order.order_items[0]
            if first_item.product and first_item.product.company:
                store_name = first_item.product.company.name
        
        # Format delivery address string
        addr_parts = []
        if isinstance(delivery_address, dict):
            addr_parts.append(delivery_address.get("address_line1") or delivery_address.get("address", ""))
            if delivery_address.get("city"):
                addr_parts.append(delivery_address.get("city"))
            if delivery_address.get("state"):
                addr_parts.append(delivery_address.get("state"))
            if delivery_address.get("pincode"):
                addr_parts.append(delivery_address.get("pincode"))
        formatted_address = ", ".join(filter(None, addr_parts)) or "Address not available"
        
        # Calculate ETA/distance placeholders
        eta_minutes = None
        distance_km = None
        if order.status in [OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY]:
            eta_minutes = 20  # Estimate
            distance_km = 3.5
        
        return {
            "id": order.id,
            "orderNumber": order.order_number,
            "order_number": order.order_number,
            "status": order.status.value,
            "storeName": store_name,
            "store_name": store_name,
            "restaurantName": store_name,
            "restaurant_name": store_name,
            "deliveryAddress": {
                "address": formatted_address,
                "address_line1": delivery_address.get("address_line1") or delivery_address.get("address", "") if isinstance(delivery_address, dict) else "",
                "city": delivery_address.get("city", "") if isinstance(delivery_address, dict) else "",
                "state": delivery_address.get("state", "") if isinstance(delivery_address, dict) else "",
                "pincode": delivery_address.get("pincode", "") if isinstance(delivery_address, dict) else "",
            },
            "delivery_address": delivery_address if isinstance(delivery_address, dict) else {"address": formatted_address},
            "totalAmount": float(order.total_amount) if order.total_amount else float(order.total),
            "total_amount": float(order.total_amount) if order.total_amount else float(order.total),
            "etaText": f"{eta_minutes} min" if eta_minutes else None,
            "distanceText": f"{distance_km} km" if distance_km else None,
            "createdAt": order.created_at.isoformat() if order.created_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
    
    # Format active order
    active_order_data = _format_order(active_order) if active_order else None
    
    # Format upcoming orders
    upcoming_orders_data = [_format_order(order) for order in upcoming_orders]
    
    return ResponseModel(
        success=True,
        data={
            "todayEarnings": round(today_earnings, 2),
            "earningsChangePercent": round(earnings_change_percent, 1),
            "completedTodayCount": len(today_delivered),
            "activeOrder": active_order_data,
            "upcomingOrders": upcoming_orders_data
        },
        message="Dashboard summary retrieved successfully"
    )
