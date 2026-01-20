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
        # Check if enum type exists
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'kycstatus')"
        ))
        enum_exists = result.scalar()
        
        if enum_exists:
            # Check if 'not_verified' value already exists
            result = connection.execute(sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'kycstatus' AND e.enumlabel = 'not_verified')"
            ))
            value_exists = result.scalar()
            
            if not value_exists:
                try:
                    connection.execute(sa.text("ALTER TYPE kycstatus ADD VALUE 'not_verified'"))
                    connection.commit()
                except Exception as e:
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

