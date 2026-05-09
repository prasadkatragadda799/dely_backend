"""add product_service_areas table

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

revision = 's2t3u4v5w6x7'
down_revision = 'r1s2t3u4v5w6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'product_service_areas',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index(
        'ix_product_service_areas_product_pincode',
        'product_service_areas',
        ['product_id', 'pincode'],
        unique=True,
    )
    op.create_index(
        'ix_product_service_areas_product_id',
        'product_service_areas',
        ['product_id'],
    )


def downgrade():
    op.drop_index('ix_product_service_areas_product_pincode', table_name='product_service_areas')
    op.drop_index('ix_product_service_areas_product_id', table_name='product_service_areas')
    op.drop_table('product_service_areas')
