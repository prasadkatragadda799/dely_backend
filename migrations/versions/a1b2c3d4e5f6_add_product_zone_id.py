"""add product zone_id

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-06-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'products',
        sa.Column('zone_id', sa.String(36), sa.ForeignKey('zones.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_products_zone_id', 'products', ['zone_id'])


def downgrade():
    op.drop_index('ix_products_zone_id', table_name='products')
    op.drop_column('products', 'zone_id')
