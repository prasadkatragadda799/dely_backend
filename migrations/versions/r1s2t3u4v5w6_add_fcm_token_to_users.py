"""add fcm_token to users

Revision ID: r1s2t3u4v5w6
Revises: q8w9e0r1t2y3
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa


revision = "r1s2t3u4v5w6"
down_revision = "q8w9e0r1t2y3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "fcm_token" not in cols:
        op.add_column("users", sa.Column("fcm_token", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "fcm_token" in cols:
        op.drop_column("users", "fcm_token")
