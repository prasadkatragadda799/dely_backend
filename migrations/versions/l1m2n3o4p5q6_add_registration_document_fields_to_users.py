"""add registration document fields to users

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa


revision = "l1m2n3o4p5q6"
down_revision = "k0l1m2n3o4p5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gst_certificate", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("fssai_license", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("udyam_registration", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("trade_certificate", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "trade_certificate")
    op.drop_column("users", "udyam_registration")
    op.drop_column("users", "fssai_license")
    op.drop_column("users", "gst_certificate")
