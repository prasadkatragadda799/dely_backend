"""make user email nullable

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'x7y8z9a0b1c2'
down_revision = 'w6x7y8z9a0b1'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'email', nullable=True)


def downgrade():
    # Backfill NULLs before reverting to NOT NULL
    op.execute("UPDATE users SET email = CONCAT(phone, '@vendor.delycart.in') WHERE email IS NULL")
    op.alter_column('users', 'email', nullable=False)
