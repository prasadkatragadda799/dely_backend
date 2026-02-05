"""add user_payment_methods table

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "g6h7i8j9k0l1"
down_revision = "f5g6h7i8j9k0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_payment_methods",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=True),
        sa.Column("brand", sa.String(length=50), nullable=True),
        sa.Column("expiry_month", sa.String(length=2), nullable=True),
        sa.Column("expiry_year", sa.String(length=4), nullable=True),
        sa.Column("upi_id", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_payment_methods_user_id", "user_payment_methods", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_user_payment_methods_user_id", table_name="user_payment_methods")
    op.drop_table("user_payment_methods")
