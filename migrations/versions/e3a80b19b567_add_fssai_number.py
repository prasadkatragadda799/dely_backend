"""add_fssai_number

Revision ID: e3a80b19b567
Revises: f5g6h7i8j9k0
Create Date: 2026-01-27 12:06:45.209962

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3a80b19b567'
down_revision = 'f5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()

    # users.fssai_number
    if "users" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("users")]
        if is_sqlite:
            with op.batch_alter_table("users", schema=None) as batch_op:
                if "fssai_number" not in user_columns:
                    batch_op.add_column(sa.Column("fssai_number", sa.String(length=14), nullable=True))
        else:
            if "fssai_number" not in user_columns:
                op.add_column("users", sa.Column("fssai_number", sa.String(length=14), nullable=True))

    # kycs.fssai_number + make kycs.pan_number nullable
    if "kycs" in existing_tables:
        kyc_columns = [col["name"] for col in inspector.get_columns("kycs")]
        if is_sqlite:
            with op.batch_alter_table("kycs", schema=None) as batch_op:
                if "fssai_number" not in kyc_columns:
                    batch_op.add_column(sa.Column("fssai_number", sa.String(length=14), nullable=True))
                if "pan_number" in kyc_columns:
                    batch_op.alter_column(
                        "pan_number",
                        existing_type=sa.String(length=10),
                        nullable=True,
                    )
        else:
            if "fssai_number" not in kyc_columns:
                op.add_column("kycs", sa.Column("fssai_number", sa.String(length=14), nullable=True))
            if "pan_number" in kyc_columns:
                op.alter_column(
                    "kycs",
                    "pan_number",
                    existing_type=sa.String(length=10),
                    nullable=True,
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()

    if "kycs" in existing_tables:
        kyc_columns = [col["name"] for col in inspector.get_columns("kycs")]
        if is_sqlite:
            with op.batch_alter_table("kycs", schema=None) as batch_op:
                if "fssai_number" in kyc_columns:
                    batch_op.drop_column("fssai_number")
                if "pan_number" in kyc_columns:
                    batch_op.alter_column(
                        "pan_number",
                        existing_type=sa.String(length=10),
                        nullable=False,
                    )
        else:
            if "fssai_number" in kyc_columns:
                op.drop_column("kycs", "fssai_number")
            if "pan_number" in kyc_columns:
                op.alter_column(
                    "kycs",
                    "pan_number",
                    existing_type=sa.String(length=10),
                    nullable=False,
                )

    if "users" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("users")]
        if is_sqlite:
            with op.batch_alter_table("users", schema=None) as batch_op:
                if "fssai_number" in user_columns:
                    batch_op.drop_column("fssai_number")
        else:
            if "fssai_number" in user_columns:
                op.drop_column("users", "fssai_number")

