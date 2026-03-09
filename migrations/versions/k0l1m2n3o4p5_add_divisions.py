"""add divisions and division_id to category, product, cart, order

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa


revision = "k0l1m2n3o4p5"
down_revision = "j9k0l1m2n3o4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create divisions table
    op.create_table(
        "divisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_divisions_name"), "divisions", ["name"], unique=False)
    op.create_index(op.f("ix_divisions_slug"), "divisions", ["slug"], unique=True)

    # Add division_id to categories, products, carts, orders
    op.add_column("categories", sa.Column("division_id", sa.String(36), nullable=True))
    op.add_column("products", sa.Column("division_id", sa.String(36), nullable=True))
    op.add_column("carts", sa.Column("division_id", sa.String(36), nullable=True))
    op.add_column("orders", sa.Column("division_id", sa.String(36), nullable=True))

    op.create_foreign_key("fk_categories_division", "categories", "divisions", ["division_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_products_division", "products", "divisions", ["division_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_carts_division", "carts", "divisions", ["division_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_orders_division", "orders", "divisions", ["division_id"], ["id"], ondelete="SET NULL")

    op.create_index(op.f("ix_categories_division_id"), "categories", ["division_id"], unique=False)
    op.create_index(op.f("ix_products_division_id"), "products", ["division_id"], unique=False)
    op.create_index(op.f("ix_carts_division_id"), "carts", ["division_id"], unique=False)
    op.create_index(op.f("ix_orders_division_id"), "orders", ["division_id"], unique=False)

    # Seed default and Kitchen divisions
    op.execute("""
        INSERT INTO divisions (id, name, slug, description, display_order, is_active, created_at, updated_at)
        VALUES
            ('00000000-0000-0000-0000-000000000001', 'Grocery', 'default', 'Default grocery division', 0, true, NOW(), NOW()),
            ('00000000-0000-0000-0000-000000000002', 'Kitchen', 'kitchen', 'Kitchen essentials & supplies', 1, true, NOW(), NOW())
    """)


def downgrade() -> None:
    op.drop_constraint("fk_orders_division", "orders", type_="foreignkey")
    op.drop_constraint("fk_carts_division", "carts", type_="foreignkey")
    op.drop_constraint("fk_products_division", "products", type_="foreignkey")
    op.drop_constraint("fk_categories_division", "categories", type_="foreignkey")
    op.drop_index(op.f("ix_orders_division_id"), table_name="orders")
    op.drop_index(op.f("ix_carts_division_id"), table_name="carts")
    op.drop_index(op.f("ix_products_division_id"), table_name="products")
    op.drop_index(op.f("ix_categories_division_id"), table_name="categories")
    op.drop_column("orders", "division_id")
    op.drop_column("carts", "division_id")
    op.drop_column("products", "division_id")
    op.drop_column("categories", "division_id")
    op.drop_index(op.f("ix_divisions_slug"), table_name="divisions")
    op.drop_index(op.f("ix_divisions_name"), table_name="divisions")
    op.drop_table("divisions")
