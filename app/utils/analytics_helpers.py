"""
Analytics helper utilities for date range and period calculations
"""
from datetime import datetime, timedelta, date
from typing import Tuple, Optional
from calendar import monthrange


def get_period_date_range(period: str, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Tuple[datetime, datetime]:
    """
    Get date range based on period parameter.
    
    Args:
        period: 'week', 'month', 'quarter', 'year', or 'all'
        date_from: Optional custom start date
        date_to: Optional custom end date
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.utcnow()
    
    # If custom dates provided, use them
    if date_from and date_to:
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())
        return start_dt, end_dt
    
    # Otherwise, calculate based on period
    if period == 'week':
        # Last 7 days
        start_dt = datetime.combine((now - timedelta(days=6)).date(), datetime.min.time())
        end_dt = datetime.combine(now.date(), datetime.max.time())
    elif period == 'month':
        # Current month
        start_dt = datetime(now.year, now.month, 1, 0, 0, 0)
        end_dt = datetime.combine(now.date(), datetime.max.time())
    elif period == 'quarter':
        # Last 3 months
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start_dt = datetime(now.year, quarter_start_month, 1, 0, 0, 0)
        end_dt = datetime.combine(now.date(), datetime.max.time())
    elif period == 'year':
        # Current year
        start_dt = datetime(now.year, 1, 1, 0, 0, 0)
        end_dt = datetime.combine(now.date(), datetime.max.time())
    else:  # 'all'
        # All time (from 2020 or earliest data)
        start_dt = datetime(2020, 1, 1, 0, 0, 0)
        end_dt = datetime.combine(now.date(), datetime.max.time())
    
    return start_dt, end_dt


def get_previous_period_date_range(start_dt: datetime, end_dt: datetime) -> Tuple[datetime, datetime]:
    """
    Calculate the previous period date range for comparison.
    
    Args:
        start_dt: Current period start date
        end_dt: Current period end date
        
    Returns:
        Tuple of (prev_start_datetime, prev_end_datetime)
    """
    period_length = (end_dt - start_dt).days
    
    prev_end_dt = start_dt - timedelta(seconds=1)
    prev_start_dt = prev_end_dt - timedelta(days=period_length)
    
    # Ensure time components
    prev_start_dt = datetime.combine(prev_start_dt.date(), datetime.min.time())
    prev_end_dt = datetime.combine(prev_end_dt.date(), datetime.max.time())
    
    return prev_start_dt, prev_end_dt


def calculate_percentage_change(current: float, previous: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Percentage change (rounded to 1 decimal place)
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    
    change = ((current - previous) / previous) * 100
    return round(change, 1)


def format_period_label(period: str, dt: datetime, index: int = 0) -> str:
    """
    Format period label based on period type.
    
    Args:
        period: 'week', 'month', 'quarter', 'year', or 'all'
        dt: Datetime to format
        index: Index number for week labels
        
    Returns:
        Formatted period label
    """
    if period == 'week':
        # Return day name (Mon, Tue, Wed, etc.)
        return dt.strftime('%a')  # Short weekday name
    elif period == 'month':
        # Return week number (Week 1, Week 2, etc.)
        return f"Week {index + 1}"
    elif period == 'quarter':
        # Return month name
        return dt.strftime('%B')  # Full month name
    elif period == 'year':
        # Return month short name (Jan, Feb, etc.)
        return dt.strftime('%b')  # Short month name
    else:  # 'all'
        # Return month and year (Jan 2024, Feb 2024, etc.)
        return dt.strftime('%b %Y')


def get_active_users_threshold() -> datetime:
    """
    Get the threshold datetime for considering a user active.
    Currently set to 7 days ago.
    
    Returns:
        Datetime threshold for active users
    """
    return datetime.utcnow() - timedelta(days=7)


def get_status_color(status: str) -> str:
    """
    Get color code for order status.
    
    Args:
        status: Order status string
        
    Returns:
        Hex color code
    """
    status_colors = {
        'delivered': '#10B981',
        'shipped': '#06b6d4',
        'confirmed': '#3b82f6',
        'pending': '#F59E0B',
        'cancelled': '#EF4444',
        'canceled': '#EF4444',
        'processing': '#8b5cf6',
        'out_for_delivery': '#14b8a6',
    }
    return status_colors.get(status.lower(), '#6B7280')


def get_payment_method_color(method: str) -> str:
    """
    Get color code for payment method.
    
    Args:
        method: Payment method string
        
    Returns:
        Hex color code
    """
    payment_colors = {
        'credit': '#1E6DD8',
        'upi': '#10B981',
        'bank_transfer': '#F59E0B',
        'cash': '#EF4444',
        'debit': '#8b5cf6',
        'wallet': '#ec4899',
    }
    return payment_colors.get(method.lower(), '#6B7280')
