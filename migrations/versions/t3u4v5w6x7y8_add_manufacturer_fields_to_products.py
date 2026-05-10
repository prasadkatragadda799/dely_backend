"""add manufacturer_name and manufacturer_address to products

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa

revision = 't3u4v5w6x7y8'
down_revision = 's2t3u4v5w6x7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('manufacturer_name', sa.String(255), nullable=True))
    op.add_column('products', sa.Column('manufacturer_address', sa.Text, nullable=True))


def downgrade():
    op.drop_column('products', 'manufacturer_address')
    op.drop_column('products', 'manufacturer_name')
