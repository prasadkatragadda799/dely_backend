from typing import List, Any, Dict
from math import ceil


def paginate(items: List[Any], page: int, limit: int, total: int = None) -> Dict[str, Any]:
    """
    Create pagination response
    """
    if total is None:
        total = len(items)
    
    total_pages = ceil(total / limit) if limit > 0 else 0
    
    return {
        "currentPage": page,
        "totalPages": total_pages,
        "totalItems": total,
        "itemsPerPage": limit,
        "hasNext": page < total_pages,
        "hasPrev": page > 1
    }

