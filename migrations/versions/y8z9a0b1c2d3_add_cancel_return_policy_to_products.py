"""add cancel_policy and return_policy to products

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'y8z9a0b1c2d3'
down_revision = 'x7y8z9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('cancel_policy', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('return_policy', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('products', 'return_policy')
    op.drop_column('products', 'cancel_policy')
