"""create order_returns table

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-06-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = 'a1b2c3d4e5f6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'order_returns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='requested'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('media_urls', JSON, nullable=True),
        sa.Column('bank_account_number', sa.String(40), nullable=True),
        sa.Column('bank_ifsc_code', sa.String(15), nullable=True),
        sa.Column('bank_account_holder', sa.String(100), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_person_id', sa.String(36), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(), nullable=True),
        sa.Column('received_at_hub_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_order_returns_order_id'),
    )
    op.create_index('ix_order_returns_order_id', 'order_returns', ['order_id'])
    op.create_index('ix_order_returns_user_id', 'order_returns', ['user_id'])


def downgrade():
    op.drop_index('ix_order_returns_user_id', table_name='order_returns')
    op.drop_index('ix_order_returns_order_id', table_name='order_returns')
    op.drop_table('order_returns')
