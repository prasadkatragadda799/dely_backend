"""
Discount calculation utilities
"""
from decimal import Decimal
from typing import Optional


def calculate_discount_percentage(mrp: Optional[Decimal], selling_price: Optional[Decimal]) -> float:
    """
    Calculate discount percentage from MRP and selling price.
    
    Args:
        mrp: Maximum Retail Price
        selling_price: Actual selling price
        
    Returns:
        Discount percentage (0-100), rounded to 2 decimal places
    """
    if not mrp or not selling_price:
        return 0.0
    
    # Convert to float for calculation
    mrp_val = float(mrp)
    selling_val = float(selling_price)
    
    # No discount if selling price >= MRP
    if mrp_val == 0 or selling_val >= mrp_val:
        return 0.0
    
    # Calculate percentage: ((MRP - Selling) / MRP) * 100
    discount = ((mrp_val - selling_val) / mrp_val) * 100
    
    # Round to 2 decimal places
    return round(discount, 2)


def calculate_savings(mrp: Optional[Decimal], selling_price: Optional[Decimal]) -> Decimal:
    """
    Calculate amount saved.
    
    Args:
        mrp: Maximum Retail Price
        selling_price: Actual selling price
        
    Returns:
        Amount saved
    """
    if not mrp or not selling_price:
        return Decimal('0.00')
    
    if selling_price >= mrp:
        return Decimal('0.00')
    
    return mrp - selling_price
