"""
Admin Invoice Endpoints
Returns the same invoice structure as the app (GET /api/v1/orders/{id}/invoice).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order
from app.models.admin import Admin
from app.api.admin_deps import require_seller_or_above
from app.utils.invoice import build_invoice_data

router = APIRouter()


@router.get("/{order_id}", response_model=ResponseModel)
async def get_order_invoice(
    order_id: str,
    admin: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Get invoice data for an order. Same structure as app invoice
    (GET /api/v1/orders/{order_id}/invoice) so admin and app show identical data.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        order = db.query(Order).filter(Order.order_number == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    user = getattr(order, "user", None)
    invoice_data = build_invoice_data(order, user, db)
    return ResponseModel(
        success=True,
        data=invoice_data,
        message="Invoice retrieved successfully"
    )
