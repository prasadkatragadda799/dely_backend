"""add_lowercase_kycstatus_enum_values

Revision ID: 2a3b4c5d6e7f
Revises: 1ef1b21e62b9
Create Date: 2026-01-08 04:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a3b4c5d6e7f'
down_revision = '1ef1b21e62b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add lowercase enum values to kycstatus enum
    # The initial migration created the enum with uppercase values (PENDING, VERIFIED, REJECTED)
    # But our Python code uses lowercase values (pending, verified, rejected, not_verified)
    # We need to add the lowercase versions to the enum
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # Add lowercase enum values
        # Note: PostgreSQL doesn't support IF NOT EXISTS for ADD VALUE in older versions
        # So we try to add and catch the error if it already exists
        lowercase_values = ['pending', 'verified', 'rejected']
        for value in lowercase_values:
            try:
                op.execute(f"ALTER TYPE kycstatus ADD VALUE '{value}'")
            except Exception as e:
                # If the value already exists, that's fine - just continue
                error_str = str(e).lower()
                if 'already exists' not in error_str and 'duplicate' not in error_str:
                    # Re-raise if it's a different error
                    raise


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment that this is not easily reversible
    pass

