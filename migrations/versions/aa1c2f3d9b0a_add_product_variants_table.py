"""add_product_variants_table

Revision ID: aa1c2f3d9b0a
Revises: 968dcd80709d
Create Date: 2026-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa1c2f3d9b0a"
down_revision = "968dcd80709d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create product_variants table if it doesn't exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "product_variants" not in existing_tables:
        op.create_table(
            "product_variants",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("hsn_code", sa.String(length=50), nullable=True),
            sa.Column("set_pcs", sa.String(length=50), nullable=True),
            sa.Column("weight", sa.String(length=50), nullable=True),
            sa.Column("mrp", sa.Numeric(10, 2), nullable=True),
            sa.Column("special_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("free_item", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_product_variants_product_id",
            "product_variants",
            ["product_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")


