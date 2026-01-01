"""add_missing_company_category_columns

Revision ID: 968dcd80709d
Revises: 788578f71cd3
Create Date: 2026-01-01 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '968dcd80709d'
down_revision = '788578f71cd3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if we're using SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    inspector = inspect(bind)
    
    # Check existing columns
    companies_cols = [col['name'] for col in inspector.get_columns('companies')]
    categories_cols = [col['name'] for col in inspector.get_columns('categories')]
    
    # Add missing columns to companies table
    if 'logo_url' not in companies_cols or 'updated_at' not in companies_cols:
        if is_sqlite:
            with op.batch_alter_table('companies', schema=None) as batch_op:
                if 'logo_url' not in companies_cols:
                    batch_op.add_column(sa.Column('logo_url', sa.String(length=500), nullable=True))
                if 'updated_at' not in companies_cols:
                    batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        else:
            if 'logo_url' not in companies_cols:
                op.add_column('companies', sa.Column('logo_url', sa.String(length=500), nullable=True))
            if 'updated_at' not in companies_cols:
                op.add_column('companies', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Add missing columns to categories table
    if 'slug' not in categories_cols or 'display_order' not in categories_cols or 'is_active' not in categories_cols or 'updated_at' not in categories_cols:
        if is_sqlite:
            with op.batch_alter_table('categories', schema=None) as batch_op:
                if 'slug' not in categories_cols:
                    batch_op.add_column(sa.Column('slug', sa.String(length=255), nullable=True))
                if 'display_order' not in categories_cols:
                    batch_op.add_column(sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'))
                if 'is_active' not in categories_cols:
                    batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
                if 'updated_at' not in categories_cols:
                    batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
                # Create index for slug if it doesn't exist
                existing_indexes = [idx['name'] for idx in inspector.get_indexes('categories')]
                if 'ix_categories_slug' not in existing_indexes:
                    batch_op.create_index('ix_categories_slug', ['slug'], unique=True)
        else:
            if 'slug' not in categories_cols:
                op.add_column('categories', sa.Column('slug', sa.String(length=255), nullable=True))
            if 'display_order' not in categories_cols:
                op.add_column('categories', sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'))
            if 'is_active' not in categories_cols:
                op.add_column('categories', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
            if 'updated_at' not in categories_cols:
                op.add_column('categories', sa.Column('updated_at', sa.DateTime(), nullable=True))
            # Create index for slug
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('categories')]
            if 'ix_categories_slug' not in existing_indexes:
                op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)


def downgrade() -> None:
    # Remove columns (optional, for rollback)
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        with op.batch_alter_table('categories', schema=None) as batch_op:
            batch_op.drop_index('ix_categories_slug')
            batch_op.drop_column('updated_at')
            batch_op.drop_column('is_active')
            batch_op.drop_column('display_order')
            batch_op.drop_column('slug')
        with op.batch_alter_table('companies', schema=None) as batch_op:
            batch_op.drop_column('updated_at')
            batch_op.drop_column('logo_url')
    else:
        op.drop_index('ix_categories_slug', table_name='categories')
        op.drop_column('categories', 'updated_at')
        op.drop_column('categories', 'is_active')
        op.drop_column('categories', 'display_order')
        op.drop_column('categories', 'slug')
        op.drop_column('companies', 'updated_at')
        op.drop_column('companies', 'logo_url')
