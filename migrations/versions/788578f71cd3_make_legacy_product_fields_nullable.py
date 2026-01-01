"""make_legacy_product_fields_nullable

Revision ID: 788578f71cd3
Revises: add_admin_panel
Create Date: 2026-01-01 18:38:46.115237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '788578f71cd3'
down_revision = 'add_admin_panel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make legacy product fields nullable (they are deprecated)
    # Check if we're using SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        # SQLite doesn't support ALTER COLUMN directly, use batch_alter_table
        with op.batch_alter_table('products', schema=None) as batch_op:
            batch_op.alter_column('brand', nullable=True)
            batch_op.alter_column('price', nullable=True)
            batch_op.alter_column('original_price', nullable=True)
            batch_op.alter_column('discount', nullable=True)
            batch_op.alter_column('stock', nullable=True)
            batch_op.alter_column('min_order', nullable=True)
            batch_op.alter_column('rating', nullable=True)
            batch_op.alter_column('reviews_count', nullable=True)
    else:
        # PostgreSQL/MySQL support ALTER COLUMN
        op.alter_column('products', 'brand', nullable=True)
        op.alter_column('products', 'price', nullable=True)
        op.alter_column('products', 'original_price', nullable=True)
        op.alter_column('products', 'discount', nullable=True)
        op.alter_column('products', 'stock', nullable=True)
        op.alter_column('products', 'min_order', nullable=True)
        op.alter_column('products', 'rating', nullable=True)
        op.alter_column('products', 'reviews_count', nullable=True)


def downgrade() -> None:
    # Revert legacy fields to NOT NULL (not recommended, but included for completeness)
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        with op.batch_alter_table('products', schema=None) as batch_op:
            batch_op.alter_column('brand', nullable=False)
            batch_op.alter_column('price', nullable=False)
            batch_op.alter_column('original_price', nullable=False)
            batch_op.alter_column('discount', nullable=False)
            batch_op.alter_column('stock', nullable=False)
            batch_op.alter_column('min_order', nullable=False)
            batch_op.alter_column('rating', nullable=False)
            batch_op.alter_column('reviews_count', nullable=False)
    else:
        op.alter_column('products', 'brand', nullable=False)
        op.alter_column('products', 'price', nullable=False)
        op.alter_column('products', 'original_price', nullable=False)
        op.alter_column('products', 'discount', nullable=False)
        op.alter_column('products', 'stock', nullable=False)
        op.alter_column('products', 'min_order', nullable=False)
        op.alter_column('products', 'rating', nullable=False)
        op.alter_column('products', 'reviews_count', nullable=False)
