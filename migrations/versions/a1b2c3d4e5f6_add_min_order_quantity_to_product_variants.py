"""add min_order_quantity to product_variants

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product_variants') as batch_op:
        batch_op.add_column(
            sa.Column('min_order_quantity', sa.Integer(), nullable=False, server_default='1')
        )


def downgrade():
    with op.batch_alter_table('product_variants') as batch_op:
        batch_op.drop_column('min_order_quantity')
