"""add delivery system

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2026-01-20 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5g6h7i8j9k0'
down_revision = 'e4f5g6h7i8j9'
branch_labels = None
depends_on = None


def upgrade():
    # Create delivery_persons table
    op.create_table('delivery_persons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('employee_id', sa.String(length=50), nullable=True),
        sa.Column('license_number', sa.String(length=50), nullable=True),
        sa.Column('vehicle_number', sa.String(length=50), nullable=True),
        sa.Column('vehicle_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_latitude', sa.Float(), nullable=True),
        sa.Column('current_longitude', sa.Float(), nullable=True),
        sa.Column('last_location_update', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_delivery_persons_phone', 'delivery_persons', ['phone'], unique=True)
    op.create_index('idx_delivery_persons_email', 'delivery_persons', ['email'], unique=True)
    op.create_index('idx_delivery_persons_employee_id', 'delivery_persons', ['employee_id'], unique=True)
    op.create_index('idx_delivery_persons_is_available', 'delivery_persons', ['is_available'], unique=False)
    op.create_index('idx_delivery_persons_is_online', 'delivery_persons', ['is_online'], unique=False)
    
    # Add delivery_person_id to orders table
    op.add_column('orders', sa.Column('delivery_person_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_orders_delivery_person_id',
        'orders', 'delivery_persons',
        ['delivery_person_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_orders_delivery_person_id', 'orders', ['delivery_person_id'], unique=False)


def downgrade():
    # Drop foreign key and column from orders
    op.drop_index('idx_orders_delivery_person_id', table_name='orders')
    op.drop_constraint('fk_orders_delivery_person_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'delivery_person_id')
    
    # Drop indexes
    op.drop_index('idx_delivery_persons_is_online', table_name='delivery_persons')
    op.drop_index('idx_delivery_persons_is_available', table_name='delivery_persons')
    op.drop_index('idx_delivery_persons_employee_id', table_name='delivery_persons')
    op.drop_index('idx_delivery_persons_email', table_name='delivery_persons')
    op.drop_index('idx_delivery_persons_phone', table_name='delivery_persons')
    
    # Drop table
    op.drop_table('delivery_persons')
