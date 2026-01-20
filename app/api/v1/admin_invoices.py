"""
Admin Invoice Endpoints
Provides invoice data in Udaan-style format for admin panel
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import ResponseModel
from app.models.order import Order, OrderItem
from app.models.admin import Admin
from app.api.admin_deps import require_seller_or_above
import random
import string

router = APIRouter()


def generate_shipment_number():
    """Generate a random shipment number in format SGHA175KPR4FYJ"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=3))
    letters2 = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers2 = ''.join(random.choices(string.digits, k=1))
    letters3 = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"{letters}{numbers}{letters2}{numbers2}{letters3}"


def get_state_code(state_name: str) -> str:
    """Get state code from state name"""
    state_codes = {
        "andhra pradesh": "37",
        "arunachal pradesh": "12",
        "assam": "18",
        "bihar": "10",
        "chhattisgarh": "22",
        "goa": "30",
        "gujarat": "24",
        "haryana": "06",
        "himachal pradesh": "02",
        "jharkhand": "20",
        "karnataka": "29",
        "kerala": "32",
        "madhya pradesh": "23",
        "maharashtra": "27",
        "manipur": "14",
        "meghalaya": "17",
        "mizoram": "15",
        "nagaland": "13",
        "odisha": "21",
        "punjab": "03",
        "rajasthan": "08",
        "sikkim": "11",
        "tamil nadu": "33",
        "telangana": "36",
        "tripura": "16",
        "uttar pradesh": "09",
        "uttarakhand": "05",
        "west bengal": "19",
        "andaman and nicobar islands": "35",
        "chandigarh": "04",
        "dadra and nagar haveli and daman and diu": "26",
        "delhi": "07",
        "jammu and kashmir": "01",
        "ladakh": "38",
        "lakshadweep": "31",
        "puducherry": "34",
    }
    return state_codes.get(state_name.lower(), "09")


@router.get("/{order_id}", response_model=ResponseModel)
async def get_order_invoice(
    order_id: str,
    admin: Admin = Depends(require_seller_or_above),
    db: Session = Depends(get_db)
):
    """
    Get invoice data for an order in Udaan-style format.
    Returns JSON data structure for frontend invoice display.
    """
    # Get order with relationships
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Get user/customer info
    customer_name = "Customer"
    customer_mobile = "+91 0000000000"
    customer_address = ""
    customer_city = ""
    customer_state = ""
    customer_pincode = ""
    customer_state_code = "09"
    
    if order.user:
        customer_name = order.user.name or "Customer"
        customer_mobile = order.user.phone or "+91 0000000000"
    
    # Get delivery address
    if order.delivery_address:
        addr = order.delivery_address
        customer_address = addr.get("address") or addr.get("street") or ""
        customer_city = addr.get("city") or ""
        customer_state = addr.get("state") or ""
        customer_pincode = addr.get("pincode") or addr.get("zip_code") or ""
        
        # Get state code
        if customer_state:
            customer_state_code = get_state_code(customer_state)
        
        # Use phone from delivery address if not in user
        if not customer_mobile or customer_mobile == "+91 0000000000":
            customer_mobile = addr.get("phone") or addr.get("mobile") or "+91 0000000000"
    
    # Generate shipment number if not present
    shipment_number = order.tracking_number or generate_shipment_number()
    
    # Build items array with all required fields
    items = []
    for order_item in order.order_items:
        product = order_item.product
        if not product:
            continue
        
        # Get variant if available
        variant = None
        if hasattr(product, 'variants') and product.variants:
            # For now, we assume first variant or can be enhanced
            variant = product.variants[0] if product.variants else None
        
        # Get HSN code with fallback chain
        hsn_code = "07139090"  # Default fallback
        if variant and variant.hsn_code:
            hsn_code = variant.hsn_code
        elif product and hasattr(product, 'hsn_code') and product.hsn_code:
            hsn_code = product.hsn_code
        
        # Get pricing
        mrp = float(product.mrp) if product.mrp else 0.0
        selling_price = float(order_item.price) if order_item.price else float(product.selling_price) if product.selling_price else 0.0
        quantity = order_item.quantity
        
        # Calculate tax (default 0 if not stored)
        cgst_rate = 0.0
        sgst_rate = 0.0
        taxable_amount = selling_price * quantity
        cgst_amount = (taxable_amount * cgst_rate) / 100
        sgst_amount = (taxable_amount * sgst_rate) / 100
        total_amount = taxable_amount + cgst_amount + sgst_amount
        
        # Get set pieces
        set_pieces = 1
        if variant and variant.set_pcs:
            try:
                set_pieces = int(variant.set_pcs) if variant.set_pcs.isdigit() else 1
            except:
                set_pieces = 1
        
        # Build item data with both camelCase and snake_case
        item_data = {
            "id": order_item.id,
            "productId": product.id,
            "product_id": product.id,
            "productName": product.name,
            "product_name": product.name,
            "productDescription": product.description or "",
            "product_description": product.description or "",
            "quantity": quantity,
            "qty": quantity,
            "mrp": mrp,
            "originalPrice": mrp,
            "sellingPrice": selling_price,
            "selling_price": selling_price,
            "price": selling_price,
            "unit": product.unit or "EACH",
            "setPieces": set_pieces,
            "set_pieces": set_pieces,
            "hsnCode": hsn_code,
            "hsn_code": hsn_code,
            "cgstRate": cgst_rate,
            "cgst_rate": cgst_rate,
            "sgstRate": sgst_rate,
            "sgst_rate": sgst_rate,
            "cgstAmount": cgst_amount,
            "cgst_amount": cgst_amount,
            "sgstAmount": sgst_amount,
            "sgst_amount": sgst_amount,
            "taxableAmount": taxable_amount,
            "taxable_amount": taxable_amount,
            "totalAmount": total_amount,
            "total_amount": total_amount,
            
            # Nested product object
            "product": {
                "id": product.id,
                "name": product.name,
                "description": product.description or "",
                "mrp": mrp,
                "sellingPrice": float(product.selling_price) if product.selling_price else 0.0,
                "selling_price": float(product.selling_price) if product.selling_price else 0.0,
                "unit": product.unit or "EACH",
                "hsnCode": hsn_code,
                "hsn_code": hsn_code
            },
            
            # Nested variant object
            "variant": {
                "id": variant.id if variant else None,
                "hsnCode": variant.hsn_code if variant else hsn_code,
                "hsn_code": variant.hsn_code if variant else hsn_code,
                "setPieces": set_pieces,
                "set_pieces": set_pieces,
                "mrp": float(variant.mrp) if variant and variant.mrp else mrp,
                "specialPrice": float(variant.special_price) if variant and variant.special_price else selling_price,
                "special_price": float(variant.special_price) if variant and variant.special_price else selling_price
            } if variant else None
        }
        
        items.append(item_data)
    
    # Build customer object
    customer = {
        "name": customer_name,
        "mobile": customer_mobile,
        "phone": customer_mobile,
        "address": customer_address,
        "city": customer_city,
        "state": customer_state,
        "pincode": customer_pincode,
        "stateCode": customer_state_code,
        "state_code": customer_state_code
    }
    
    # Build shipping address object
    shipping_address = {
        "address": customer_address,
        "city": customer_city,
        "state": customer_state,
        "pincode": customer_pincode,
        "phone": customer_mobile,
        "stateCode": customer_state_code,
        "state_code": customer_state_code
    }
    
    # Calculate totals
    total_amount = float(order.total_amount) if order.total_amount else 0.0
    subtotal = float(order.subtotal) if order.subtotal else total_amount
    tax_amount = float(order.tax) if order.tax else 0.0
    delivery_charge = float(order.delivery_charge) if order.delivery_charge else 0.0
    discount = float(order.discount) if order.discount else 0.0
    
    # Build response data
    invoice_data = {
        "id": order.id,
        "orderNumber": order.order_number,
        "order_number": order.order_number,
        "shipmentNumber": shipment_number,
        "shipment_number": shipment_number,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "invoiceDate": order.created_at.isoformat() if order.created_at else None,
        "invoice_date": order.created_at.isoformat() if order.created_at else None,
        
        "customer": customer,
        "shippingAddress": shipping_address,
        "shipping_address": shipping_address,
        
        "items": items,
        "orderItems": items,  # Alternative field name
        "order_items": items,  # Alternative field name
        "products": items,  # Alternative field name
        
        "totalAmount": total_amount,
        "total_amount": total_amount,
        "total": total_amount,
        "subtotal": subtotal,
        "taxAmount": tax_amount,
        "tax_amount": tax_amount,
        "deliveryCharge": delivery_charge,
        "delivery_charge": delivery_charge,
        "discount": discount,
        "grandTotal": total_amount,
        "grand_total": total_amount
    }
    
    return ResponseModel(
        success=True,
        data=invoice_data,
        message="Invoice retrieved successfully"
    )
