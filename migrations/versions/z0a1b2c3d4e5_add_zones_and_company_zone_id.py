"""add zones and company zone_id

Revision ID: z0a1b2c3d4e5
Revises: y8z9a0b1c2d3
Create Date: 2026-05-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'z0a1b2c3d4e5'
down_revision = 'y8z9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade():
    # Create zones table
    op.create_table(
        'zones',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_zones_name', 'zones', ['name'], unique=True)

    # Create zone_pincodes table
    op.create_table(
        'zone_pincodes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('zone_id', sa.String(36), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('zone_id', 'pincode', name='uq_zone_pincode'),
    )
    op.create_index('ix_zone_pincodes_zone_id', 'zone_pincodes', ['zone_id'])
    op.create_index('ix_zone_pincodes_pincode', 'zone_pincodes', ['pincode'])

    # Add zone_id FK column to companies
    op.add_column(
        'companies',
        sa.Column('zone_id', sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        'fk_companies_zone_id',
        'companies', 'zones',
        ['zone_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_companies_zone_id', 'companies', ['zone_id'])


def downgrade():
    op.drop_index('ix_companies_zone_id', table_name='companies')
    op.drop_constraint('fk_companies_zone_id', 'companies', type_='foreignkey')
    op.drop_column('companies', 'zone_id')

    op.drop_index('ix_zone_pincodes_pincode', table_name='zone_pincodes')
    op.drop_index('ix_zone_pincodes_zone_id', table_name='zone_pincodes')
    op.drop_table('zone_pincodes')

    op.drop_index('ix_zones_name', table_name='zones')
    op.drop_table('zones')
