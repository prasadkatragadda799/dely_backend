"""Fix product DELETE: CASCADE on carts/wishlists, SET NULL on order_items.product_id

Revision ID: o1p2q3r4s5t6
Revises: n8o9p0q1r2s3
Create Date: 2026-04-04

PostgreSQL (production): drop legacy FKs without ON DELETE and recreate with
CASCADE / SET NULL so admin DELETE /product no longer raises IntegrityError.
Other dialects: no-op; application code still removes cart/wishlist rows explicitly.
"""
from alembic import op
import sqlalchemy as sa


revision = "o1p2q3r4s5t6"
down_revision = "n8o9p0q1r2s3"
branch_labels = None
depends_on = None


def _fk_name_to_products(inspector, table: str):
    for fk in inspector.get_foreign_keys(table):
        cols = fk.get("constrained_columns") or []
        if fk.get("referred_table") == "products" and "product_id" in cols:
            return fk["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    if "carts" not in inspector.get_table_names():
        return

    # carts.product_id -> ON DELETE CASCADE
    fk = _fk_name_to_products(inspector, "carts")
    if fk:
        op.drop_constraint(fk, "carts", type_="foreignkey")
    op.create_foreign_key(
        "fk_carts_product_id_products",
        "carts",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )

    inspector = sa.inspect(bind)
    fk = _fk_name_to_products(inspector, "wishlists")
    if fk:
        op.drop_constraint(fk, "wishlists", type_="foreignkey")
    op.create_foreign_key(
        "fk_wishlists_product_id_products",
        "wishlists",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )

    inspector = sa.inspect(bind)
    fk = _fk_name_to_products(inspector, "order_items")
    if fk:
        op.drop_constraint(fk, "order_items", type_="foreignkey")

    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_order_items_product_id_products",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Reverting FK behavior risks failures if NULL product_ids or orphan rows exist; leave as no-op.
    pass
