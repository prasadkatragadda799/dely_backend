"""add hsn_code to products

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2026-01-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4f5g6h7i8j9'
down_revision = 'd3e4f5g6h7i8'
branch_labels = None
depends_on = None


def upgrade():
    # Add hsn_code column to products table
    op.add_column('products', sa.Column('hsn_code', sa.String(length=50), nullable=True))
    
    # Create index for faster HSN code lookups
    op.create_index('idx_products_hsn_code', 'products', ['hsn_code'], unique=False)


def downgrade():
    # Drop index
    op.drop_index('idx_products_hsn_code', table_name='products')
    
    # Drop column
    op.drop_column('products', 'hsn_code')
