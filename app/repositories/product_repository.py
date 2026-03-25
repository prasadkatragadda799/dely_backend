"""
Product data access. Builds filtered queries for list endpoints.
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, cast, exists, or_, select, String
from sqlalchemy.orm import Session, joinedload, Query

from app.models.admin import Admin, AdminRole
from app.models.product import Product
from app.repositories.base import BaseRepository
from app.core.constants import ExpiryFilter


class ProductRepository(BaseRepository[Product]):
    """Repository for Product model with filter helpers."""

    def __init__(self, db: Session):
        super().__init__(Product, db)

    def get_by_id_with_relations(
        self,
        product_id: str,
        load_images: bool = True,
        load_variants: bool = True,
        load_brand: bool = True,
        load_company: bool = True,
        load_category: bool = True,
    ) -> Optional[Product]:
        """Get product by id (or uuid string) with optional relations."""
        options = []
        if load_images:
            options.append(joinedload(Product.product_images))
        if load_variants:
            options.append(joinedload(Product.variants))
        if load_brand:
            options.append(joinedload(Product.brand_rel))
        if load_company:
            options.append(joinedload(Product.company))
        if load_category:
            options.append(joinedload(Product.category))
        q = self.db.query(Product)
        for opt in options:
            q = q.options(opt)
        # Support both UUID with and without dashes (DB may store either)
        product_id_alt = product_id.replace("-", "") if "-" in product_id else product_id
        ids_to_try = [product_id] if product_id == product_id_alt else [product_id, product_id_alt]
        return q.filter(Product.id.in_(ids_to_try)).first()

    def build_admin_list_query(
        self,
        *,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        company_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        created_by_admin_id: Optional[UUID] = None,
        listing_scope: Optional[str] = None,
        status: Optional[str] = None,
        stock_status: Optional[str] = None,
        expiry_within_months: Optional[int] = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Query:
        """
        Build filtered and ordered query for admin product list.
        Caller can use .count(), .offset().limit().all(), and .options(joinedload(...)).

        listing_scope:
          - "seller": only products created by an admin with role seller
          - "platform": products not created by a seller (includes legacy rows with no creator)
        """
        q = self.db.query(Product)

        if created_by_admin_id is not None:
            q = q.filter(Product.created_by == str(created_by_admin_id))

        if listing_scope == "seller":
            q = q.join(
                Admin,
                and_(
                    cast(Admin.id, String) == Product.created_by,
                    Admin.role == AdminRole.SELLER,
                ),
            )
        elif listing_scope == "platform":
            seller_creator = exists(
                select(1).select_from(Admin).where(
                    and_(
                        cast(Admin.id, String) == Product.created_by,
                        Admin.role == AdminRole.SELLER,
                    )
                )
            )
            q = q.filter(~seller_creator)

        if search:
            q = q.filter(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.slug.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                )
            )
        if category_id:
            q = q.filter(Product.category_id == str(category_id))
        if company_id:
            q = q.filter(Product.company_id == str(company_id))
        if brand_id:
            q = q.filter(Product.brand_id == str(brand_id))

        if status == "available":
            q = q.filter(Product.is_available == True)
        elif status == "unavailable":
            q = q.filter(Product.is_available == False)

        if stock_status == "in_stock":
            q = q.filter(Product.stock_quantity > 10)
        elif stock_status == "low_stock":
            q = q.filter(
                and_(
                    Product.stock_quantity > 0,
                    Product.stock_quantity <= 10,
                )
            )
        elif stock_status == "out_of_stock":
            q = q.filter(Product.stock_quantity == 0)

        if expiry_within_months is not None:
            today = date.today()
            end_date = today + timedelta(
                days=expiry_within_months * ExpiryFilter.DAYS_PER_MONTH_APPROX
            )
            q = q.filter(
                Product.expiry_date.isnot(None),
                Product.expiry_date >= today,
                Product.expiry_date <= end_date,
            )

        order_by = Product.created_at.desc() if order == "desc" else Product.created_at.asc()
        if sort == "name":
            order_by = Product.name.asc() if order == "asc" else Product.name.desc()
        elif sort == "price":
            order_by = (
                Product.selling_price.asc()
                if order == "asc"
                else Product.selling_price.desc()
            )
        elif sort == "stock":
            order_by = (
                Product.stock_quantity.asc()
                if order == "asc"
                else Product.stock_quantity.desc()
            )
        q = q.order_by(order_by)

        return q
