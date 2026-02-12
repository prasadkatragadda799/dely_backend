"""
Application constants. Avoid magic numbers and strings across the codebase.
"""
from typing import Final


class PaginationDefaults:
    """Default pagination limits and bounds."""

    DEFAULT_PAGE: Final[int] = 1
    DEFAULT_LIMIT: Final[int] = 20
    MAX_LIMIT: Final[int] = 100
    MAX_LIMIT_ADMIN: Final[int] = 10_000


class StockStatus:
    """Stock status filter values (align with API query params)."""

    IN_STOCK: Final[str] = "in_stock"
    LOW_STOCK: Final[str] = "low_stock"
    OUT_OF_STOCK: Final[str] = "out_of_stock"


class ProductStatus:
    """Product availability filter values."""

    AVAILABLE: Final[str] = "available"
    UNAVAILABLE: Final[str] = "unavailable"
    ALL: Final[str] = "all"


class ExpiryFilter:
    """Expiry filter bounds for inventory (months)."""

    MIN_MONTHS: Final[int] = 1
    MAX_MONTHS: Final[int] = 24
    DAYS_PER_MONTH_APPROX: Final[int] = 30
