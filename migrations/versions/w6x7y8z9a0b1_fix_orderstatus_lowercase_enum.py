"""Fix orderstatus enum: add lowercase + missing values for PostgreSQL

The initial migration created the orderstatus enum with uppercase labels
(PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED).
The Python OrderStatus enum uses lowercase values (pending, confirmed, ...).
PostgreSQL enum comparison is case-sensitive, so INSERT with a lowercase value
raises: "invalid input value for enum orderstatus" → 500 on every order creation.

Also adds: out_for_delivery, completed, canceled (new statuses in OrderStatus).

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa


revision = "w6x7y8z9a0b1"
down_revision = "v5w6x7y8z9a0"
branch_labels = None
depends_on = None

_ALL_NEEDED = [
    "pending",
    "confirmed",
    "processing",
    "shipped",
    "out_for_delivery",
    "delivered",
    "completed",
    "cancelled",
    "canceled",
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus')")
    )
    if not result.scalar():
        return

    for value in _ALL_NEEDED:
        exists = bind.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM pg_enum e"
                "  JOIN pg_type t ON e.enumtypid = t.oid"
                "  WHERE t.typname = 'orderstatus' AND e.enumlabel = :v"
                ")"
            ),
            {"v": value},
        ).scalar()
        if not exists:
            bind.execute(
                sa.text(f"ALTER TYPE orderstatus ADD VALUE '{value}'")
            )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; leave as no-op.
    pass
