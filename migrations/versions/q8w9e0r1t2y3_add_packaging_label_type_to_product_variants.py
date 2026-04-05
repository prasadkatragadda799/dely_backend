"""add packaging_label_type to product_variants

Revision ID: q8w9e0r1t2y3
Revises: p2q3r4s5t6u7
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa


revision = "q8w9e0r1t2y3"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_variants" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("product_variants")}
    if "packaging_label_type" not in cols:
        op.add_column(
            "product_variants",
            sa.Column("packaging_label_type", sa.String(length=32), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_variants" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("product_variants")}
    if "packaging_label_type" in cols:
        op.drop_column("product_variants", "packaging_label_type")
