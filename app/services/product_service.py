"""
Product business logic. Delegates data access to ProductRepository.
Use from API layer (routes); keep routes thin.
"""
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.core.exceptions import NotFoundError
from app.core.constants import PaginationDefaults, ExpiryFilter


class ProductService:
    """Product use cases: list, get, and (later) create/update via repository."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)

    def list_products_for_admin(
        self,
        *,
        page: int = PaginationDefaults.DEFAULT_PAGE,
        limit: int = PaginationDefaults.DEFAULT_LIMIT,
        search: Optional[str] = None,
        category: Optional[UUID] = None,
        company: Optional[UUID] = None,
        brand: Optional[UUID] = None,
        status: Optional[str] = None,
        stock_status: Optional[str] = None,
        expiry_within_months: Optional[int] = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[List[Product], int]:
        """
        Return (products, total) for admin list with filters and pagination.
        Products are loaded with images, variants, brand, company, category.
        """
        query = self.repo.build_admin_list_query(
            search=search,
            category_id=category,
            company_id=company,
            brand_id=brand,
            status=status,
            stock_status=stock_status,
            expiry_within_months=expiry_within_months,
            sort=sort or "created_at",
            order=order or "desc",
        )
        query = query.options(
            joinedload(Product.product_images),
            joinedload(Product.variants),
            joinedload(Product.brand_rel),
            joinedload(Product.company),
            joinedload(Product.category),
        )
        total = query.count()
        offset = (page - 1) * limit
        products = query.offset(offset).limit(limit).all()
        return products, total

    def get_product_for_admin(self, product_id: str) -> Product:
        """Get a single product by id with relations. Raises NotFoundError if missing."""
        product = self.repo.get_by_id_with_relations(
            product_id,
            load_images=True,
            load_variants=True,
        )
        if not product:
            raise NotFoundError("Product not found", resource="product")
        # Ensure relations are loaded for response
        if not product.brand_rel and getattr(product, "brand_id", None):
            self.db.refresh(product)
        return product
