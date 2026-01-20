"""add user location and activity tracking

Revision ID: b1a2c3d4e5f6
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1a2c3d4e5f6'
down_revision = '2a3b4c5d6e7f'
branch_labels = None
depends_on = None


def upgrade():
    # Add location and activity tracking fields to users table
    op.add_column('users', sa.Column('city', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('state', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('pincode', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('last_active_at', sa.DateTime(), nullable=True))
    
    # Create user_activity_logs table
    op.create_table('user_activity_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('location_city', sa.String(length=255), nullable=True),
        sa.Column('location_state', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_user_activity_user_id', 'user_activity_logs', ['user_id'], unique=False)
    op.create_index('idx_user_activity_created_at', 'user_activity_logs', ['created_at'], unique=False)
    op.create_index('idx_user_activity_location', 'user_activity_logs', ['location_city', 'location_state'], unique=False)
    op.create_index('idx_user_activity_user_date', 'user_activity_logs', ['user_id', 'created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_user_activity_user_date', table_name='user_activity_logs')
    op.drop_index('idx_user_activity_location', table_name='user_activity_logs')
    op.drop_index('idx_user_activity_created_at', table_name='user_activity_logs')
    op.drop_index('idx_user_activity_user_id', table_name='user_activity_logs')
    
    # Drop user_activity_logs table
    op.drop_table('user_activity_logs')
    
    # Remove columns from users table
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'pincode')
    op.drop_column('users', 'state')
    op.drop_column('users', 'city')
