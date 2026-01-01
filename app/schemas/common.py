from typing import Optional, Any, Dict, List
from pydantic import BaseModel


class ResponseModel(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class PaginationModel(BaseModel):
    """Pagination metadata"""
    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int
    hasNext: bool
    hasPrev: bool


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    pagination: PaginationModel

