"""add product_variant_images and purchasable variant refs on cart/order_items

Revision ID: vimg1a2b3c4d
Revises: z0a1b2c3d4e5
Create Date: 2026-05-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'vimg1a2b3c4d'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # SQLite can't ALTER TABLE ADD CONSTRAINT; the column-level FK still applies via
    # the model on create_all. On Postgres/MySQL we add the named FK constraints.
    supports_alter_fk = bind.dialect.name != "sqlite"

    # Per-variant image gallery
    op.create_table(
        'product_variant_images',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('product_variant_id', sa.String(36), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_product_variant_images_product_variant_id', 'product_variant_images', ['product_variant_id'])

    # Deterministic variant ordering (matches admin form order; used for image association)
    op.add_column('product_variants', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))

    # Make a variant the purchasable SKU on the cart line
    op.add_column('carts', sa.Column('variant_id', sa.String(36), nullable=True))
    if supports_alter_fk:
        op.create_foreign_key(
            'fk_carts_variant_id',
            'carts', 'product_variants',
            ['variant_id'], ['id'],
            ondelete='SET NULL',
        )
    op.create_index('ix_carts_variant_id', 'carts', ['variant_id'])

    # Snapshot the purchased variant on the order line
    op.add_column('order_items', sa.Column('variant_id', sa.String(36), nullable=True))
    op.add_column('order_items', sa.Column('variant_label', sa.String(255), nullable=True))
    if supports_alter_fk:
        op.create_foreign_key(
            'fk_order_items_variant_id',
            'order_items', 'product_variants',
            ['variant_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    bind = op.get_bind()
    supports_alter_fk = bind.dialect.name != "sqlite"

    if supports_alter_fk:
        op.drop_constraint('fk_order_items_variant_id', 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'variant_label')
    op.drop_column('order_items', 'variant_id')

    op.drop_index('ix_carts_variant_id', table_name='carts')
    if supports_alter_fk:
        op.drop_constraint('fk_carts_variant_id', 'carts', type_='foreignkey')
    op.drop_column('carts', 'variant_id')

    op.drop_column('product_variants', 'sort_order')

    op.drop_index('ix_product_variant_images_product_variant_id', table_name='product_variant_images')
    op.drop_table('product_variant_images')
