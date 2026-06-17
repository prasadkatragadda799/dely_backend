"""
Invoice generation utilities.
Single source of truth for invoice JSON so admin and app return the same structure.
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from app.config import settings


_GST_STATE_CODES: Dict[str, str] = {
    "jammu and kashmir": "01", "himachal pradesh": "02", "punjab": "03",
    "chandigarh": "04", "uttarakhand": "05", "haryana": "06", "delhi": "07",
    "rajasthan": "08", "uttar pradesh": "09", "bihar": "10", "sikkim": "11",
    "arunachal pradesh": "12", "nagaland": "13", "manipur": "14", "mizoram": "15",
    "tripura": "16", "meghalaya": "17", "assam": "18", "west bengal": "19",
    "jharkhand": "20", "odisha": "21", "chhattisgarh": "22", "madhya pradesh": "23",
    "gujarat": "24", "daman and diu": "25", "dadra and nagar haveli": "26",
    "maharashtra": "27", "andhra pradesh": "28", "karnataka": "29", "goa": "30",
    "lakshadweep": "31", "kerala": "32", "tamil nadu": "33", "puducherry": "34",
    "andaman and nicobar islands": "35", "telangana": "36", "andhra pradesh (new)": "37",
}


def get_state_code(state_name: str) -> str:
    """Return the 2-digit GST state code for a given state name."""
    return _GST_STATE_CODES.get((state_name or "").strip().lower(), "")


def get_seller_info() -> Dict[str, Any]:
    """
    Get seller/company information for invoices.
    This can be configured via environment variables or database settings.
    """
    # For now, use environment variables or defaults
    # In production, this should come from a settings/company table
    return {
        "name": settings.SELLER_NAME if hasattr(settings, 'SELLER_NAME') else "FOODISTIC MARKETING SERVICES PVT LTD",
        "company_name": settings.SELLER_NAME if hasattr(settings, 'SELLER_NAME') else "FOODISTIC MARKETING SERVICES PVT LTD",
        "address_line1": settings.SELLER_ADDRESS_LINE1 if hasattr(settings, 'SELLER_ADDRESS_LINE1') else "No 331, Sarai Jagarnath",
        "address_line2": settings.SELLER_ADDRESS_LINE2 if hasattr(settings, 'SELLER_ADDRESS_LINE2') else "pargana - Nizamabad, Tehsil - Sadar, Janpad & Dist - Azamgarh",
        "address": f"{settings.SELLER_ADDRESS_LINE1 if hasattr(settings, 'SELLER_ADDRESS_LINE1') else 'No 331, Sarai Jagarnath'}, {settings.SELLER_ADDRESS_LINE2 if hasattr(settings, 'SELLER_ADDRESS_LINE2') else 'pargana - Nizamabad, Tehsil - Sadar, Janpad & Dist - Azamgarh'}",
        "city": settings.SELLER_CITY if hasattr(settings, 'SELLER_CITY') else "Azamgarh",
        "state": settings.SELLER_STATE if hasattr(settings, 'SELLER_STATE') else "Uttar Pradesh",
        "pincode": settings.SELLER_PINCODE if hasattr(settings, 'SELLER_PINCODE') else "276207",
        "gstin": settings.SELLER_GSTIN if hasattr(settings, 'SELLER_GSTIN') else "09AAFCF9954N1ZQ",
        "gst_number": settings.SELLER_GSTIN if hasattr(settings, 'SELLER_GSTIN') else "09AAFCF9954N1ZQ",
        "pan": settings.SELLER_PAN if hasattr(settings, 'SELLER_PAN') else "AAFCF9954N",
        "phone": settings.SELLER_PHONE if hasattr(settings, 'SELLER_PHONE') else "+91 XXXXX XXXXX",
        "email": settings.SELLER_EMAIL if hasattr(settings, 'SELLER_EMAIL') else "company@example.com",
        "logo_url": (
            (settings.SELLER_LOGO_URL or "").strip()
            if hasattr(settings, "SELLER_LOGO_URL")
            else ""
        )
        or None,
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
    seller_state_code = get_state_code(seller.get("state", ""))
    seller["state_code"] = seller_state_code
    seller["state_with_code"] = f"{seller_state_code} - {seller.get('state', '')}" if seller_state_code else seller.get("state", "")

    delivery_address = order.delivery_address if isinstance(order.delivery_address, dict) else {}
    buyer_name = delivery_address.get("name") or (user.name if user else "")
    buyer_address_line1 = delivery_address.get("address_line1") or delivery_address.get("address") or ""
    buyer_address_line2 = delivery_address.get("address_line2") or delivery_address.get("landmark") or ""
    buyer_city = delivery_address.get("city") or ""
    buyer_state = delivery_address.get("state") or ""
    buyer_pincode = delivery_address.get("pincode") or ""
    buyer_gstin = delivery_address.get("gstin") or (user.gst_number if user else "") or ""
    buyer_phone = delivery_address.get("phone") or (user.phone if user else "") or ""
    buyer_email = delivery_address.get("email") or (user.email if user and getattr(user, "email", None) else "") or ""
    buyer_state_code = get_state_code(buyer_state)

    buyer = {
        "name": buyer_name,
        "address_line1": buyer_address_line1,
        "address_line2": buyer_address_line2,
        "city": buyer_city,
        "state": buyer_state,
        "state_code": buyer_state_code,
        "state_with_code": f"{buyer_state_code} - {buyer_state}" if buyer_state_code else buyer_state,
        "pincode": buyer_pincode,
        "gstin": buyer_gstin,
        "phone": buyer_phone,
        "email": buyer_email,
    }

    supply_type = determine_supply_type(seller["state"], buyer_state)
    _pos_state = buyer_state if buyer_state else seller["state"]
    _pos_code = get_state_code(_pos_state)
    place_of_supply = f"{_pos_code} - {_pos_state.upper()}" if _pos_code else _pos_state.upper()

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
        variant_cgst: Optional[float] = None
        variant_sgst: Optional[float] = None
        if product:
            # Find the specific ordered variant (if any) so we use its tax rates.
            ordered_variant = None
            if item.variant_id and hasattr(product, "variants") and product.variants:
                ordered_variant = next(
                    (v for v in product.variants if str(v.id) == str(item.variant_id)), None
                )
            ref_variant = ordered_variant or (product.variants[0] if hasattr(product, "variants") and product.variants else None)
            if ref_variant:
                hsn_code = ref_variant.hsn_code if ref_variant.hsn_code else None
                variant_name = (
                    f"{ref_variant.set_pcs or product.unit} ({ref_variant.weight or 'Set of 1'})"
                    if ref_variant.set_pcs or ref_variant.weight
                    else product.unit
                )
                _cgst = getattr(ref_variant, "cgst", None)
                _sgst = getattr(ref_variant, "sgst", None)
                if _cgst is not None:
                    variant_cgst = float(_cgst)
                if _sgst is not None:
                    variant_sgst = float(_sgst)
            if not hsn_code:
                hsn_code = product.hsn_code or "07139090"
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

        # MRP / selling_price is GST-inclusive. Extract base (excl. GST) and tax.
        # base = price / (1 + rate/100), tax = price - base
        # Prefer the variant-stored CGST+SGST rates over HSN lookup when set.
        if variant_cgst is not None and variant_sgst is not None and (variant_cgst + variant_sgst) > 0:
            tax_rate = variant_cgst + variant_sgst
        else:
            tax_rate = calculate_tax_rate(hsn_code)
        divisor = Decimal("1") + Decimal(str(tax_rate)) / Decimal("100")
        base_price = selling_price / divisor          # per-unit excl. GST
        tax_per_unit = selling_price - base_price     # per-unit GST portion
        mrp_base = mrp / divisor                      # MRP excl. GST (for display)

        taxable_amount = base_price * quantity        # total excl. GST
        item_tax_total = tax_per_unit * quantity      # total GST on this line
        item_total = selling_price * quantity         # = taxable_amount + item_tax_total

        unit_discount = mrp - selling_price if mrp > selling_price else Decimal("0")
        discount = unit_discount * quantity

        taxes = calculate_item_taxes(
            taxable_amount, tax_rate, supply_type, seller["state"], buyer_state
        )

        total_taxable_amount += taxable_amount
        total_sgst += taxes["sgst"]
        total_cgst += taxes["cgst"]
        total_igst += taxes["igst"]

        if supply_type == "INTRASTATE":
            for tax_type in ("SGST", "CGST"):
                t_amt = taxes["sgst"] if tax_type == "SGST" else taxes["cgst"]
                if t_amt > 0:
                    key = (tax_type, tax_rate)
                    if key not in tax_details_dict:
                        tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                    tax_details_dict[key]["taxable_amount"] += taxable_amount
                    tax_details_dict[key]["tax_amount"] += t_amt
        else:
            if taxes["igst"] > 0:
                key = ("IGST", tax_rate)
                if key not in tax_details_dict:
                    tax_details_dict[key] = {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0")}
                tax_details_dict[key]["taxable_amount"] += taxable_amount
                tax_details_dict[key]["tax_amount"] += taxes["igst"]

        invoice_item = {
            "id": str(item.id),
            "product": {
                "id": str(product.id) if product else None,
                "name": (product.name if product else None) or item.product_name or "Product",
                "hsn": hsn_code,
                "variant": variant_name or (product.unit if product else "EACH (Set of 1)"),
            },
            "quantity": float(quantity),
            # MRP columns (tax-inclusive, as printed on pack)
            "original_rate": float(mrp),
            "original_price": float(mrp),
            "mrp": float(mrp),
            "mrp_excl_tax": float(mrp_base),
            # Discount
            "unit_discount": float(unit_discount),
            "discount": float(discount),
            # Rate excl. GST (taxable base per unit)
            "rate_excl_tax": float(base_price),
            "rate": float(selling_price),           # kept for legacy compatibility
            "selling_price": float(selling_price),
            "price": float(selling_price),
            # Taxable base (excl. GST) for the whole line
            "taxable_amount": float(taxable_amount),
            # GST components
            "sgst": float(taxes["sgst"]),
            "cgst": float(taxes["cgst"]),
            "tax_details": {
                "sgst": float(taxes["sgst"]),
                "cgst": float(taxes["cgst"]),
                "igst": float(taxes["igst"]),
                "rate": tax_rate,
                "total_tax": float(item_tax_total),
            },
            # Total = MRP × qty (tax already included, NOT added again)
            "total_amount": float(item_total),
        }
        invoice_items.append(invoice_item)

    # Single source of truth: the invoice totals mirror what the order was actually
    # charged (order.total_amount), so the invoice, the QR, and the orders list always
    # agree. Fall back to recomputed line-item sums for legacy rows missing totals.
    subtotal = (
        Decimal(str(order.subtotal)) if getattr(order, "subtotal", None) is not None
        else total_taxable_amount
    )
    total_tax = (
        Decimal(str(order.tax)) if getattr(order, "tax", None) is not None
        else (total_sgst + total_cgst + total_igst)
    )
    delivery_charge = Decimal(str(order.delivery_charge)) if order.delivery_charge else Decimal("0")
    grand_total = (
        Decimal(str(order.total_amount)) if getattr(order, "total_amount", None) is not None
        else (subtotal + total_tax + delivery_charge)
    )
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

    # Bank details for the invoice footer (editable from admin settings).
    bank_details = None
    try:
        from app.api.v1.admin_settings import get_setting as _get_setting
        bd = _get_setting(db, "bank") or {}
        if any(bd.get(k) for k in ("bankName", "accountNumber", "ifscCode")):
            bank_details = {
                "bankName": bd.get("bankName", ""),
                "accountHolderName": bd.get("accountHolderName", ""),
                "accountNumber": bd.get("accountNumber", ""),
                "ifscCode": bd.get("ifscCode", ""),
                "branchName": bd.get("branchName", ""),
            }
    except Exception:
        pass

    # Dynamic UPI QR: pay the exact invoice total to the business UPI ID, with the
    # invoice number as the transaction note/reference. No payment gateway needed.
    upi_qr = None
    try:
        from app.api.v1.admin_settings import get_setting
        from app.utils.upi import build_upi_uri, qr_png_data_uri
        payment = get_setting(db, "payment") or {}
        vpa = (payment.get("upiId") or "").strip()
        if vpa:
            payee = (payment.get("upiPayeeName") or "DelyCart").strip()
            uri = build_upi_uri(
                vpa, payee, float(rounded_total),
                note=f"Invoice {invoice_number}", ref=invoice_number,
            )
            upi_qr = {
                "upiUri": uri,
                "qrImage": qr_png_data_uri(uri),
                "amount": round(float(rounded_total), 2),
                "vpa": vpa,
                "payeeName": payee,
                "invoiceNumber": invoice_number,
            }
    except Exception as exc:
        # Don't let QR generation break the invoice, but make the reason visible
        # (e.g. the `qrcode` package not installed in the deployed environment).
        import logging
        logging.getLogger(__name__).warning("Invoice UPI QR generation failed: %s", exc, exc_info=True)
        upi_qr = None

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
        "upiQr": upi_qr,
        "bankDetails": bank_details,
        "paid_amount": float(rounded_total) if getattr(order, "payment_status", None) == "paid" else float(0),
        "balance": float(0) if getattr(order, "payment_status", None) == "paid" else float(rounded_total),
        "savings": float(savings),
        "tax_payable_reverse_charge": False,
        "terms": "This transaction/sales is subject to TDS U/s 194-O hence TDS U/s 194Q is not applicable. This is a computer-generated invoice. For any issues, please contact Customer Care team.",
        "notes": getattr(order, "notes", None) or "Thanks for doing business with us!",
    }

