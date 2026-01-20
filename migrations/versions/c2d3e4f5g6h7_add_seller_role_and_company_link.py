"""add seller role and company link

Revision ID: c2d3e4f5g6h7
Revises: b1a2c3d4e5f6
Create Date: 2026-01-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c2d3e4f5g6h7'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'seller' to AdminRole enum
    # Only for PostgreSQL - SQLite doesn't have enum types
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # Check if enum type exists
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'adminrole')"
        ))
        enum_exists = result.scalar()
        
        if enum_exists:
            # Check if 'seller' value already exists
            result = connection.execute(sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'adminrole' AND e.enumlabel = 'seller')"
            ))
            value_exists = result.scalar()
            
            if not value_exists:
                # Add the new enum value
                connection.execute(sa.text("ALTER TYPE adminrole ADD VALUE 'seller'"))
                connection.commit()
    
    # Add company_id column to admins table
    op.add_column('admins', sa.Column('company_id', sa.String(length=36), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_admins_company_id',
        'admins', 'companies',
        ['company_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index on company_id
    op.create_index('idx_admins_company_id', 'admins', ['company_id'], unique=False)


def downgrade():
    # Drop index
    op.drop_index('idx_admins_company_id', table_name='admins')
    
    # Drop foreign key
    op.drop_constraint('fk_admins_company_id', 'admins', type_='foreignkey')
    
    # Drop column
    op.drop_column('admins', 'company_id')
    
    # Note: PostgreSQL doesn't support removing enum values easily
    # You would need to create a new enum without 'seller' and migrate data
    # For simplicity, we're leaving the enum value in place on downgrade
