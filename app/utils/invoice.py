"""
Invoice generation utilities
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
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

