"""Optional set and remaining tier prices; cart.price_option_key

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-04-04

- products: set_selling_price, set_mrp, remaining_selling_price, remaining_mrp (nullable)
- carts: price_option_key VARCHAR default 'unit'
"""
from alembic import op
import sqlalchemy as sa


revision = "p2q3r4s5t6u7"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "products" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("products")}
        if "set_selling_price" not in cols:
            op.add_column(
                "products",
                sa.Column("set_selling_price", sa.Numeric(10, 2), nullable=True),
            )
        if "set_mrp" not in cols:
            op.add_column("products", sa.Column("set_mrp", sa.Numeric(10, 2), nullable=True))
        if "remaining_selling_price" not in cols:
            op.add_column(
                "products",
                sa.Column("remaining_selling_price", sa.Numeric(10, 2), nullable=True),
            )
        if "remaining_mrp" not in cols:
            op.add_column(
                "products",
                sa.Column("remaining_mrp", sa.Numeric(10, 2), nullable=True),
            )

    if "carts" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("carts")}
        if "price_option_key" not in cols:
            op.add_column(
                "carts",
                sa.Column(
                    "price_option_key",
                    sa.String(20),
                    nullable=False,
                    server_default="unit",
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "carts" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("carts")}
        if "price_option_key" in cols:
            op.drop_column("carts", "price_option_key")
    if "products" in inspector.get_table_names():
        for col in (
            "remaining_mrp",
            "remaining_selling_price",
            "set_mrp",
            "set_selling_price",
        ):
            cols = {c["name"] for c in inspector.get_columns("products")}
            if col in cols:
                op.drop_column("products", col)
