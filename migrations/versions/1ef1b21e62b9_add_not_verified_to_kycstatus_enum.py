"""add_not_verified_to_kycstatus_enum

Revision ID: 1ef1b21e62b9
Revises: aa1c2f3d9b0a
Create Date: 2026-01-07 19:10:35.749780

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1ef1b21e62b9'
down_revision = 'aa1c2f3d9b0a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'not_verified' to the kycstatus enum
    # The database enum was created with uppercase values, but we need lowercase
    # Check database type
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # For PostgreSQL, use ALTER TYPE to add the new enum value
        # Note: PostgreSQL enum values are case-sensitive
        # The enum was created with uppercase, but we're using lowercase in Python
        # We need to add 'not_verified' (lowercase) to match the Python enum
        try:
            op.execute("ALTER TYPE kycstatus ADD VALUE IF NOT EXISTS 'not_verified'")
        except Exception as e:
            # If the value already exists, that's fine
            if 'already exists' not in str(e).lower():
                raise
    # For SQLite, enum is stored as string, so no migration needed
    # The model change is sufficient


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment that this is not easily reversible
    # In production, you might need to:
    # 1. Create a new enum type with the old values
    # 2. Alter the columns to use the new type
    # 3. Drop the old enum type
    pass

