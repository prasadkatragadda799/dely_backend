"""seed home division

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-05-11

"""
from alembic import op
import sqlalchemy as sa

revision = "v5w6x7y8z9a0"
down_revision = "u4v5w6x7y8z9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO divisions (id, name, slug, description, display_order, is_active, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000003', 'Home', 'home', 'Home essentials & décor', 2, true, NOW(), NOW())
        ON CONFLICT (slug) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM divisions WHERE slug = 'home'")
