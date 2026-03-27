"""add product commission_cost

Revision ID: 9c1f0f7b2f3a
Revises: f3e84693ebfa
Create Date: 2026-03-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c1f0f7b2f3a"
down_revision = "f3e84693ebfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("commission_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "check_commission_cost_non_negative",
        "products",
        "commission_cost >= 0",
    )
    op.alter_column("products", "commission_cost", server_default=None)


def downgrade() -> None:
    op.drop_constraint("check_commission_cost_non_negative", "products", type_="check")
    op.drop_column("products", "commission_cost")
