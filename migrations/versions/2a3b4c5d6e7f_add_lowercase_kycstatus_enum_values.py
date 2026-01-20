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
        # Check if enum type exists
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'kycstatus')"
        ))
        enum_exists = result.scalar()
        
        if enum_exists:
            # Add lowercase enum values
            lowercase_values = ['pending', 'verified', 'rejected']
            for value in lowercase_values:
                # Check if value already exists
                result = connection.execute(sa.text(
                    f"SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'kycstatus' AND e.enumlabel = '{value}')"
                ))
                value_exists = result.scalar()
                
                if not value_exists:
                    try:
                        connection.execute(sa.text(f"ALTER TYPE kycstatus ADD VALUE '{value}'"))
                        connection.commit()
                    except Exception as e:
                        error_str = str(e).lower()
                        if 'already exists' not in error_str and 'duplicate' not in error_str:
                            raise


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment that this is not easily reversible
    pass

