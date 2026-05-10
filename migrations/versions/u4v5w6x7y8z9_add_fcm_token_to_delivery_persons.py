"""add fcm_token to delivery_persons

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa


revision = "u4v5w6x7y8z9"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "delivery_persons" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("delivery_persons")}
    if "fcm_token" not in cols:
        op.add_column(
            "delivery_persons",
            sa.Column("fcm_token", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "delivery_persons" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("delivery_persons")}
    if "fcm_token" in cols:
        op.drop_column("delivery_persons", "fcm_token")
