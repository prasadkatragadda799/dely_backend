"""add_category_metadata_fields

Revision ID: 51a1c2753e8e
Revises: add_admin_panel
Create Date: 2026-01-02 12:11:57.203604

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite


# revision identifiers, used by Alembic.
revision = '51a1c2753e8e'
down_revision = '3c33fd45178d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Determine database type
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    # Check if columns already exist
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('categories')] if 'categories' in inspector.get_table_names() else []
    
    # Add description column
    if 'description' not in existing_columns:
        op.add_column('categories', sa.Column('description', sa.Text(), nullable=True))
    
    # Add image column
    if 'image' not in existing_columns:
        op.add_column('categories', sa.Column('image', sa.String(length=500), nullable=True))
    
    # Add meta_title column
    if 'meta_title' not in existing_columns:
        op.add_column('categories', sa.Column('meta_title', sa.String(length=255), nullable=True))
    
    # Add meta_description column
    if 'meta_description' not in existing_columns:
        op.add_column('categories', sa.Column('meta_description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('categories', 'meta_description')
    op.drop_column('categories', 'meta_title')
    op.drop_column('categories', 'image')
    op.drop_column('categories', 'description')
