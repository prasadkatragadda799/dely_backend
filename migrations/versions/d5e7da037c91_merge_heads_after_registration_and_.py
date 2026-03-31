"""merge heads after registration and commission migrations

Revision ID: d5e7da037c91
Revises: l1m2n3o4p5q6, 9c1f0f7b2f3a
Create Date: 2026-03-31 06:45:45.736721

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e7da037c91'
down_revision = ('l1m2n3o4p5q6', '9c1f0f7b2f3a')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

