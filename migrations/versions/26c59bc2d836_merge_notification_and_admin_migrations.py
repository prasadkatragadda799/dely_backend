"""merge notification and admin migrations

Revision ID: 26c59bc2d836
Revises: a7b8c9d0e1f2, i8j9k0l1m2n3
Create Date: 2026-02-05 11:40:58.748677

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26c59bc2d836'
down_revision = ('a7b8c9d0e1f2', 'i8j9k0l1m2n3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

