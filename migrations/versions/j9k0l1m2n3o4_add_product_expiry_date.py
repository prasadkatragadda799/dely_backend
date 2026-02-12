"""add product expiry_date

Revision ID: j9k0l1m2n3o4
Revises: f3e84693ebfa
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "j9k0l1m2n3o4"
down_revision = "f3e84693ebfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("expiry_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "expiry_date")
