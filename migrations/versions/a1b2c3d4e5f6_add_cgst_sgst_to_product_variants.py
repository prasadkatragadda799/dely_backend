"""add cgst and sgst to product_variants

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('product_variants', sa.Column('cgst', sa.Numeric(5, 2), nullable=False, server_default='0.00'))
    op.add_column('product_variants', sa.Column('sgst', sa.Numeric(5, 2), nullable=False, server_default='0.00'))


def downgrade():
    op.drop_column('product_variants', 'sgst')
    op.drop_column('product_variants', 'cgst')
