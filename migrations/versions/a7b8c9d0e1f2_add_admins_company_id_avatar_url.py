"""add admins company_id and avatar_url if missing

Revision ID: a7b8c9d0e1f2
Revises: c8b6d5a2f1e0
Create Date: 2026-02-02 12:00:00.000000

Adds company_id and avatar_url to admins table if they don't exist.
Safe for DBs that were created before c2d3e4f5g6h7 ran or where that migration was skipped.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "c8b6d5a2f1e0"
branch_labels = None
depends_on = None


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Return True if the column exists on the table."""
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    if not column_exists(conn, "admins", "company_id"):
        op.add_column(
            "admins",
            sa.Column("company_id", sa.String(length=36), nullable=True),
        )
        op.create_foreign_key(
            "fk_admins_company_id",
            "admins",
            "companies",
            ["company_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "idx_admins_company_id",
            "admins",
            ["company_id"],
            unique=False,
        )

    if not column_exists(conn, "admins", "avatar_url"):
        op.add_column(
            "admins",
            sa.Column("avatar_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    # Idempotent migration: we may not have added these columns (they could
    # exist from c2d3e4f5g6h7 / add_admin_panel_tables). Do not drop columns
    # on downgrade to avoid breaking the schema.
    pass
