"""
Core module: shared exceptions, constants, and dependency injection.
"""
from app.core.exceptions import (
    AppException,
    NotFoundError,
    ValidationError as AppValidationError,
    ForbiddenError,
    ConflictError,
)
from app.core.constants import (
    PaginationDefaults,
    StockStatus,
)

__all__ = [
    "AppException",
    "NotFoundError",
    "AppValidationError",
    "ForbiddenError",
    "ConflictError",
    "PaginationDefaults",
    "StockStatus",
]
