"""
Invoice generation utilities.
Single source of truth for invoice JSON so admin and app return the same structure.
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from app.config import settings


def get_seller_info() -> Dict[str, Any]:
    """
    Get seller/company information for invoices.
    This can be configured via environment variables or database settings.
    """
    # For now, use environment variables or defaults
    # In production, this should come from a settings/company table
    return {
        "name": settings.SELLER_NAME if hasattr(settings, 'SELLER_NAME') else "GRANARY WHOLESALE PRIVATE LIMITED",
        "company_name": settings.SELLER_NAME if hasattr(settings, 'SELLER_NAME') else "GRANARY WHOLESALE PRIVATE LIMITED",
        "address_line1": settings.SELLER_ADDRESS_LINE1 if hasattr(settings, 'SELLER_ADDRESS_LINE1') else "No 331, Sarai Jagarnath",
        "address_line2": settings.SELLER_ADDRESS_LINE2 if hasattr(settings, 'SELLER_ADDRESS_LINE2') else "pargana - Nizamabad, Tehsil - Sadar, Janpad & Dist - Azamgarh",
        "address": f"{settings.SELLER_ADDRESS_LINE1 if hasattr(settings, 'SELLER_ADDRESS_LINE1') else 'No 331, Sarai Jagarnath'}, {settings.SELLER_ADDRESS_LINE2 if hasattr(settings, 'SELLER_ADDRESS_LINE2') else 'pargana - Nizamabad, Tehsil - Sadar, Janpad & Dist - Azamgarh'}",
        "city": settings.SELLER_CITY if hasattr(settings, 'SELLER_CITY') else "Azamgarh",
        "state": settings.SELLER_STATE if hasattr(settings, 'SELLER_STATE') else "Uttar Pradesh",
        "pincode": settings.SELLER_PINCODE if hasattr(settings, 'SELLER_PINCODE') else "276207",
        "gstin": settings.SELLER_GSTIN if hasattr(settings, 'SELLER_GSTIN') else "09AAHCG7552R1ZP",
        "gst_number": settings.SELLER_GSTIN if hasattr(settings, 'SELLER_GSTIN') else "09AAHCG7552R1ZP",
        "pan": settings.SELLER_PAN if hasattr(settings, 'SELLER_PAN') else "AAHCG7552R",
        "fssai": settings.SELLER_FSSAI if hasattr(settings, 'SELLER_FSSAI') else "10019043002791",
        "fssai_link": settings.SELLER_FSSAI_LINK if hasattr(settings, 'SELLER_FSSAI_LINK') else "https://foscos.fssai.gov.in/",
        "phone": settings.SELLER_PHONE if hasattr(settings, 'SELLER_PHONE') else "+91 XXXXX XXXXX",
        "email": settings.SELLER_EMAIL if hasattr(settings, 'SELLER_EMAIL') else "company@example.com"
    }


def calculate_tax_rate(hsn_code: Optional[str], product_category: Optional[str] = None) -> float:
    """
    Calculate tax rate based on HSN code and product category.
    Default GST rates for common categories:
    - Food items: 0% or 5%
    - General goods: 18%
    - Luxury items: 28%
    """
    if not hsn_code:
        return 18.0  # Default 18% GST
    
    # Extract first 2 digits of HSN code for category
    try:
        hsn_prefix = int(hsn_code[:2]) if len(hsn_code) >= 2 else 0
    except ValueError:
        return 18.0
    
    # Food items (HSN 07-09, 10-15)
    if 7 <= hsn_prefix <= 15:
        return 5.0  # 5% GST for food items
    
    # General goods
    if 16 <= hsn_prefix <= 24:
        return 18.0  # 18% GST
    
    # Default to 18%
    return 18.0


def determine_supply_type(seller_state: str, buyer_state: str) -> str:
    """Determine if supply is INTRASTATE or INTERSTATE"""
    if seller_state.upper() == buyer_state.upper():
        return "INTRASTATE"
    return "INTERSTATE"


def calculate_item_taxes(
    taxable_amount: Decimal,
    tax_rate: float,
    supply_type: str,
    seller_state: str,
    buyer_state: str
) -> Dict[str, Decimal]:
    """
    Calculate SGST, CGST, or IGST based on supply type
    Returns: {"sgst": amount, "cgst": amount, "igst": amount}
    """
    tax_amount = Decimal(str(taxable_amount)) * Decimal(str(tax_rate)) / Decimal("100")
    
    if supply_type == "INTRASTATE":
        # Split tax equally between SGST and CGST
        half_tax = tax_amount / Decimal("2")
        return {
            "sgst": half_tax,
            "cgst": half_tax,
            "igst": Decimal("0")
        }
    else:
        # Interstate - use IGST
        return {
            "sgst": Decimal("0"),
            "cgst": Decimal("0"),
            "igst": tax_amount
        }


def generate_invoice_number(order_id: str, order_number: str) -> str:
    """
    Generate invoice number from order.
    Format can be customized (e.g., "INV-2024-001" or "GY7Y91/250000008")
    """
    # For now, use order number as base
    # In production, use sequential invoice numbers
    year = datetime.now().year
    # Extract last part of order number or use order ID
    invoice_suffix = order_number.split('-')[-1] if '-' in order_number else order_id[:8].upper()
    return f"INV-{year}-{invoice_suffix}"


def calculate_savings(items: list) -> Decimal:
    """
    Calculate total savings from discounts.
    Savings = Sum of (MRP - Selling Price) × Quantity for all items
    """
    total_savings = Decimal("0")
    for item in items:
        mrp = Decimal(str(item.get("mrp", 0) or item.get("original_rate", 0) or 0))
        selling_price = Decimal(str(item.get("selling_price", 0) or item.get("rate", 0) or item.get("price", 0) or 0))
        quantity = Decimal(str(item.get("quantity", 0) or 1))
        
        discount_per_unit = mrp - selling_price
        if discount_per_unit > 0:
            total_savings += discount_per_unit * quantity
    
    return total_savings


def round_to_nearest_rupee(amount: Decimal) -> Tuple[Decimal, Decimal]:
    """
    Round amount to nearest rupee.
    Returns: (rounded_amount, round_off)
    """
    rounded = round(amount)
    round_off = Decimal(str(rounded)) - amount
    return Decimal(str(rounded)), round_off


def build_invoice_data(order: Any, user: Any, db: Session) -> Dict[str, Any]:
    """
    Build the canonical invoice JSON for an order.
    Used by both app (GET /api/v1/orders/{id}/invoice) and admin (GET /admin/orders/{id}/invoice)
    so admin and app receive exactly the same invoice structure.
    """
    from app.models.order import Order, OrderItem
    from app.models.product import Product

    seller = get_seller_info()
    delivery_address = order.delivery_address if isinstance(order.delivery_address, dict) else {}
    buyer_name = delivery_address.get("name") or (user.name if user else "")
    buyer_address_line1 = delivery_address.get("address_line1") or delivery_address.get("address") or ""
    buyer_address_line2 = delivery_address.get("address_line2") or delivery_address.get("landmark") or ""
    buyer_city = delivery_address.get("city") or ""
    buyer_state = delivery_address.get("state") or ""
    buyer_pincode = delivery_address.get("pincode") or ""
    buyer_gstin = delivery_address.get("gstin") or (user.gst_number if user else "") or ""
    buyer_phone = delivery_address.get("phone") or (user.phone if user else "") or ""

    buyer = {
        "name": buyer_name,
        "address_line1": buyer_address_line1,
        "address_line2": buyer_address_line2,
        "city": buyer_city,
        "state": buyer_state,
        "pincode": buyer_pincode,
        "gstin": buyer_gstin,
        "phone": buyer_phone,
    }

    supply_type = determine_supply_type(seller["state"], buyer_state)
    place_of_supply = buyer_state.upper() if buyer_state else seller["state"].upper()

    order_items = db.query(OrderItem).filter(OrderItem.order_id == str(order.id)).all()
    invoice_items = []
    tax_details_dict = {}
    total_taxable_amount = Decimal("0")
    total_sgst = Decimal("0")
    total_cgst = Decimal("0")
    total_igst = Decimal("0")

    for item in order_items:
        product = None
        if item.product_id:
            product = (
                db.query(Product)
                .options(joinedload(Product.variants))
                .filter(Product.id == str(item.product_id))
                .first()
            )

        hsn_code = None
        variant_name = None
        if product:
            if hasattr(product, "variants") and product.variants:
                first_variant = product.variants[0]
                hsn_code = first_variant.hsn_code if first_variant.hsn_code else None
                variant_name = (
                    f"{first_variant.set_pcs or product.unit} ({first_variant.weight or 'Set of 1'})"
                    if first_variant.set_pcs or first_variant.weight
                    else product.unit
                )
            if not hsn_code:
                hsn_code = "07139090"
            if not variant_name:
                variant_name = product.unit or "EACH (Set of 1)"

        mrp = (
            Decimal(str(product.mrp))
            if product and product.mrp
            else Decimal(str(item.price or 0)) * Decimal("1.2")
        )
        selling_price = (
            Decimal(str(item.price))
            if item.price
            else (Decimal(str(product.selling_price)) if product and product.selling_price else Decimal("0"))
        )
        quantity = Decimal(str(item.quantity))

        unit_discount = mrp - selling_price if mrp > selling_price else Decimal("0")
        discount = unit_discount * quantity
        taxable_amount = selling_price * quantity
        tax_rate = calculate_tax_rate(hsn_code)
        taxes = calculate_item_taxes(
            taxable_amount, tax_rate, supply_type, seller["state"], buyer_state
        )

        total_taxable_amount += taxable_amount
        total_sgst += taxes["sgst"]
        total_cgst += taxes["cgst"]
        total_igst += taxes["igst"]

        if supply_type == "INTRASTATE":
            if taxes["sgst"] > 0:
                key = ("SGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["sgst"]
            if taxes["cgst"] > 0:
                key = ("CGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["cgst"]
        else:
            if taxes["igst"] > 0:
                key = ("IGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["igst"]

        item_total = taxable_amount + taxes["sgst"] + taxes["cgst"] + taxes["igst"]
        invoice_item = {
            "id": str(item.id),
            "product": {
                "id": str(product.id) if product else None,
                "name": product.name if product else (getattr(item, "product_name", None) or "Product"),
                "hsn": hsn_code,
                "variant": variant_name or (product.unit if product else "EACH (Set of 1)"),
            },
            "quantity": float(quantity),
            "original_rate": float(mrp),
            "original_price": float(mrp),
            "mrp": float(mrp),
            "unit_discount": float(unit_discount),
            "discount": float(discount),
            "rate": float(selling_price),
            "selling_price": float(selling_price),
            "price": float(selling_price),
            "taxable_amount": float(taxable_amount),
            "sgst": float(taxes["sgst"]),
            "cgst": float(taxes["cgst"]),
            "tax_details": {
                "sgst": float(taxes["sgst"]),
                "cgst": float(taxes["cgst"]),
                "igst": float(taxes["igst"]),
                "rate": tax_rate,
            },
            "total_amount": float(item_total),
        }
        invoice_items.append(invoice_item)

    subtotal = total_taxable_amount
    total_tax = total_sgst + total_cgst + total_igst
    delivery_charge = Decimal(str(order.delivery_charge)) if order.delivery_charge else Decimal("0")
    grand_total = subtotal + total_tax + delivery_charge
    rounded_total, round_off = round_to_nearest_rupee(grand_total)

    tax_details_list = []
    for (tax_type, rate), amounts in tax_details_dict.items():
        tax_details_list.append({
            "tax_type": tax_type,
            "name": tax_type,
            "taxable_amount": float(amounts["taxable_amount"]),
            "rate": rate,
            "tax_amount": float(amounts["tax_amount"]),
        })
    tax_details_list.sort(key=lambda x: (x["tax_type"], x["rate"]))

    savings = calculate_savings(invoice_items)
    invoice_number = generate_invoice_number(str(order.id), order.order_number)
    invoice_date = order.created_at if order.created_at else datetime.utcnow()
    invoice_time = invoice_date.strftime("%I:%M %p") if invoice_date else "11:00 AM"

    return {
        "invoice_number": invoice_number,
        "reference_number": invoice_number,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "shipment_number": (order.tracking_number or ""),
        "invoice_date": invoice_date.isoformat() if invoice_date else datetime.utcnow().isoformat(),
        "created_at": invoice_date.isoformat() if invoice_date else datetime.utcnow().isoformat(),
        "time": invoice_time,
        "place_of_supply": place_of_supply,
        "supply_type": supply_type,
        "page_number": "1/1",
        "seller": seller,
        "buyer": buyer,
        "items": invoice_items,
        "tax_details": tax_details_list,
        "subtotal": float(subtotal),
        "taxable_amount": float(subtotal),
        "delivery_charge": float(delivery_charge),
        "total_tax": float(total_tax),
        "round_off": float(round_off),
        "total": float(rounded_total),
        "grand_total": float(rounded_total),
        "paid_amount": float(rounded_total) if getattr(order, "payment_status", None) == "paid" else float(0),
        "balance": float(0) if getattr(order, "payment_status", None) == "paid" else float(rounded_total),
        "savings": float(savings),
        "tax_payable_reverse_charge": False,
        "terms": "This transaction/sales is subject to TDS U/s 194-O hence TDS U/s 194Q is not applicable. This is a computer-generated invoice. For any issues, please contact Customer Care team.",
        "notes": getattr(order, "notes", None) or "Thanks for doing business with us!",
    }

