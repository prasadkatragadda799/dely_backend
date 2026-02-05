"""add offers updated_at

Revision ID: f3e84693ebfa
Revises: 26c59bc2d836
Create Date: 2026-02-05 12:00:01.640800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3e84693ebfa'
down_revision = '26c59bc2d836'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "offers",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_column("offers", "updated_at")

