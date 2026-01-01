"""add_admin_panel_tables

Revision ID: add_admin_panel
Revises: 6140177ab80d
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = 'add_admin_panel'
down_revision = '6140177ab80d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Determine database type
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    # Use String(36) for SQLite, UUID for PostgreSQL
    uuid_type = sa.String(length=36) if is_sqlite else postgresql.UUID(as_uuid=True)
    json_type = sa.Text() if is_sqlite else postgresql.JSON
    
    # Check if tables already exist (for partial migrations)
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create admins table
    if 'admins' not in existing_tables:
        op.create_table(
        'admins',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
        op.create_index(op.f('ix_admins_email'), 'admins', ['email'], unique=True)
    
    # Create brands table
    if 'brands' not in existing_tables:
        op.create_table(
        'brands',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('company_id', uuid_type, nullable=True),
        sa.Column('category_id', uuid_type, nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'])
    )
        op.create_index(op.f('ix_brands_name'), 'brands', ['name'], unique=False)
    
    # Create product_images table
    if 'product_images' not in existing_tables:
        op.create_table(
        'product_images',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('product_id', uuid_type, nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE')
    )
        op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)
    
    # Create order_status_history table
    if 'order_status_history' not in existing_tables:
        op.create_table(
        'order_status_history',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('order_id', uuid_type, nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('changed_by', uuid_type, nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['admins.id'])
    )
        op.create_index(op.f('ix_order_status_history_order_id'), 'order_status_history', ['order_id'], unique=False)
    
    # Create admin_activity_log table
    if 'admin_activity_log' not in existing_tables:
        op.create_table(
        'admin_activity_log',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('admin_id', uuid_type, nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', uuid_type, nullable=True),
        sa.Column('details', json_type, nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'])
    )
        op.create_index(op.f('ix_admin_activity_log_admin_id'), 'admin_activity_log', ['admin_id'], unique=False)
        op.create_index(op.f('ix_admin_activity_log_action'), 'admin_activity_log', ['action'], unique=False)
        op.create_index(op.f('ix_admin_activity_log_entity_type'), 'admin_activity_log', ['entity_type'], unique=False)
        op.create_index(op.f('ix_admin_activity_log_created_at'), 'admin_activity_log', ['created_at'], unique=False)
    
    # Create kyc_documents table
    if 'kyc_documents' not in existing_tables:
        op.create_table(
        'kyc_documents',
        sa.Column('id', uuid_type, nullable=False),
        sa.Column('user_id', uuid_type, nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_url', sa.String(length=500), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
        op.create_index(op.f('ix_kyc_documents_user_id'), 'kyc_documents', ['user_id'], unique=False)
    
    # Add new columns to products table
    # Check which columns already exist
    if 'products' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('products')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('products')]
        
        # For SQLite, we need to use batch mode for adding foreign keys
        if is_sqlite:
            with op.batch_alter_table('products', schema=None) as batch_op:
                if 'slug' not in existing_columns:
                    batch_op.add_column(sa.Column('slug', sa.String(length=255), nullable=True))
                if 'brand_id' not in existing_columns:
                    batch_op.add_column(sa.Column('brand_id', uuid_type, nullable=True))
                if 'mrp' not in existing_columns:
                    batch_op.add_column(sa.Column('mrp', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'selling_price' not in existing_columns:
                    batch_op.add_column(sa.Column('selling_price', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'stock_quantity' not in existing_columns:
                    batch_op.add_column(sa.Column('stock_quantity', sa.Integer(), nullable=True, server_default='0'))
                if 'min_order_quantity' not in existing_columns:
                    batch_op.add_column(sa.Column('min_order_quantity', sa.Integer(), nullable=True, server_default='1'))
                if 'meta_title' not in existing_columns:
                    batch_op.add_column(sa.Column('meta_title', sa.String(length=255), nullable=True))
                if 'meta_description' not in existing_columns:
                    batch_op.add_column(sa.Column('meta_description', sa.Text(), nullable=True))
                if 'created_by' not in existing_columns:
                    batch_op.add_column(sa.Column('created_by', uuid_type, nullable=True))
                # Add foreign keys only if columns were added
                if 'brand_id' not in existing_columns and 'fk_products_brand_id' not in [fk['name'] for fk in inspector.get_foreign_keys('products')]:
                    batch_op.create_foreign_key('fk_products_brand_id', 'brands', ['brand_id'], ['id'], ondelete='SET NULL')
                if 'created_by' not in existing_columns and 'fk_products_created_by' not in [fk['name'] for fk in inspector.get_foreign_keys('products')]:
                    batch_op.create_foreign_key('fk_products_created_by', 'admins', ['created_by'], ['id'])
                if 'ix_products_slug' not in existing_indexes:
                    batch_op.create_index('ix_products_slug', ['slug'], unique=True)
        else:
            if 'slug' not in existing_columns:
                op.add_column('products', sa.Column('slug', sa.String(length=255), nullable=True))
            if 'brand_id' not in existing_columns:
                op.add_column('products', sa.Column('brand_id', uuid_type, nullable=True))
            if 'mrp' not in existing_columns:
                op.add_column('products', sa.Column('mrp', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'selling_price' not in existing_columns:
                op.add_column('products', sa.Column('selling_price', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'stock_quantity' not in existing_columns:
                op.add_column('products', sa.Column('stock_quantity', sa.Integer(), nullable=True, server_default='0'))
            if 'min_order_quantity' not in existing_columns:
                op.add_column('products', sa.Column('min_order_quantity', sa.Integer(), nullable=True, server_default='1'))
            if 'meta_title' not in existing_columns:
                op.add_column('products', sa.Column('meta_title', sa.String(length=255), nullable=True))
            if 'meta_description' not in existing_columns:
                op.add_column('products', sa.Column('meta_description', sa.Text(), nullable=True))
            if 'created_by' not in existing_columns:
                op.add_column('products', sa.Column('created_by', uuid_type, nullable=True))
            # Add foreign keys and indexes
            existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('products')]
            if 'brand_id' not in existing_columns and 'fk_products_brand_id' not in existing_fks:
                op.create_foreign_key('fk_products_brand_id', 'products', 'brands', ['brand_id'], ['id'], ondelete='SET NULL')
            if 'created_by' not in existing_columns and 'fk_products_created_by' not in existing_fks:
                op.create_foreign_key('fk_products_created_by', 'products', 'admins', ['created_by'], ['id'])
            if 'ix_products_slug' not in existing_indexes:
                op.create_index(op.f('ix_products_slug'), 'products', ['slug'], unique=True)
    
    # Add new columns to categories table
    if is_sqlite:
        with op.batch_alter_table('categories', schema=None) as batch_op:
            batch_op.add_column(sa.Column('slug', sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
            batch_op.create_index('ix_categories_slug', ['slug'], unique=True)
    else:
        op.add_column('categories', sa.Column('slug', sa.String(length=255), nullable=True))
        op.add_column('categories', sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'))
        op.add_column('categories', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
        op.add_column('categories', sa.Column('updated_at', sa.DateTime(), nullable=True))
        op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)
    
    # Add new columns to companies table
    if is_sqlite:
        with op.batch_alter_table('companies', schema=None) as batch_op:
            batch_op.add_column(sa.Column('logo_url', sa.String(length=500), nullable=True))
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
    else:
        op.add_column('companies', sa.Column('logo_url', sa.String(length=500), nullable=True))
        op.add_column('companies', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Add new columns to users table
    if is_sqlite:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('pan_number', sa.String(length=10), nullable=True))
            batch_op.add_column(sa.Column('kyc_verified_at', sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column('kyc_verified_by', uuid_type, nullable=True))
            batch_op.create_foreign_key('fk_users_kyc_verified_by', 'admins', ['kyc_verified_by'], ['id'])
    else:
        op.add_column('users', sa.Column('pan_number', sa.String(length=10), nullable=True))
        op.add_column('users', sa.Column('kyc_verified_at', sa.DateTime(), nullable=True))
        op.add_column('users', sa.Column('kyc_verified_by', uuid_type, nullable=True))
        op.create_foreign_key('fk_users_kyc_verified_by', 'users', 'admins', ['kyc_verified_by'], ['id'])
    
    # Add new columns to orders table
    if is_sqlite:
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.add_column(sa.Column('payment_status', sa.String(length=20), nullable=True, server_default='pending'))
            batch_op.add_column(sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True))
            batch_op.add_column(sa.Column('tracking_number', sa.String(length=100), nullable=True))
            batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
            batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column('cancelled_reason', sa.Text(), nullable=True))
            # Note: SQLite doesn't support changing column nullability easily, so user_id remains as is
    else:
        op.add_column('orders', sa.Column('payment_status', sa.String(length=20), nullable=True, server_default='pending'))
        op.add_column('orders', sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True))
        op.add_column('orders', sa.Column('tracking_number', sa.String(length=100), nullable=True))
        op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))
        op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        op.add_column('orders', sa.Column('cancelled_reason', sa.Text(), nullable=True))
        op.alter_column('orders', 'user_id', nullable=True)
    
    # Modify order_items table
    if is_sqlite:
        with op.batch_alter_table('order_items', schema=None) as batch_op:
            batch_op.add_column(sa.Column('product_name', sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column('product_image_url', sa.String(length=500), nullable=True))
            batch_op.add_column(sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True))
            batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
    else:
        op.add_column('order_items', sa.Column('product_name', sa.String(length=255), nullable=True))
        op.add_column('order_items', sa.Column('product_image_url', sa.String(length=500), nullable=True))
        op.add_column('order_items', sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True))
        op.add_column('order_items', sa.Column('created_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Drop new tables
    op.drop_table('kyc_documents')
    op.drop_table('admin_activity_log')
    op.drop_table('order_status_history')
    op.drop_table('product_images')
    op.drop_table('brands')
    op.drop_table('admins')
    
    # Remove columns from products
    op.drop_index(op.f('ix_products_slug'), table_name='products')
    op.drop_constraint('fk_products_created_by', 'products', type_='foreignkey')
    op.drop_constraint('fk_products_brand_id', 'products', type_='foreignkey')
    op.drop_column('products', 'created_by')
    op.drop_column('products', 'meta_description')
    op.drop_column('products', 'meta_title')
    op.drop_column('products', 'min_order_quantity')
    op.drop_column('products', 'stock_quantity')
    op.drop_column('products', 'selling_price')
    op.drop_column('products', 'mrp')
    op.drop_column('products', 'brand_id')
    op.drop_column('products', 'slug')
    
    # Remove columns from categories
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_column('categories', 'updated_at')
    op.drop_column('categories', 'is_active')
    op.drop_column('categories', 'display_order')
    op.drop_column('categories', 'slug')
    
    # Remove columns from companies
    op.drop_column('companies', 'updated_at')
    op.drop_column('companies', 'logo_url')
    
    # Remove columns from users
    op.drop_constraint('fk_users_kyc_verified_by', 'users', type_='foreignkey')
    op.drop_column('users', 'kyc_verified_by')
    op.drop_column('users', 'kyc_verified_at')
    op.drop_column('users', 'pan_number')
    
    # Remove columns from orders
    op.drop_column('orders', 'cancelled_reason')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'notes')
    op.drop_column('orders', 'tracking_number')
    op.drop_column('orders', 'total_amount')
    op.drop_column('orders', 'payment_status')
    
    # Remove columns from order_items
    op.drop_column('order_items', 'created_at')
    op.drop_column('order_items', 'unit_price')
    op.drop_column('order_items', 'product_image_url')
    op.drop_column('order_items', 'product_name')

