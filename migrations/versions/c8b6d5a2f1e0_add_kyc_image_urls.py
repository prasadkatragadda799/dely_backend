"""add kyc image urls

Revision ID: c8b6d5a2f1e0
Revises: e3a80b19b567
Create Date: 2026-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8b6d5a2f1e0"
down_revision = "e3a80b19b567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if "kycs" not in existing_tables:
        return

    kyc_columns = [col["name"] for col in inspector.get_columns("kycs")]

    if is_sqlite:
        with op.batch_alter_table("kycs", schema=None) as batch_op:
            if "shop_image_url" not in kyc_columns:
                batch_op.add_column(sa.Column("shop_image_url", sa.String(length=500), nullable=True))
            if "fssai_license_image_url" not in kyc_columns:
                batch_op.add_column(sa.Column("fssai_license_image_url", sa.String(length=500), nullable=True))
    else:
        if "shop_image_url" not in kyc_columns:
            op.add_column("kycs", sa.Column("shop_image_url", sa.String(length=500), nullable=True))
        if "fssai_license_image_url" not in kyc_columns:
            op.add_column("kycs", sa.Column("fssai_license_image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_tables = inspector.get_table_names()
    if "kycs" not in existing_tables:
        return

    kyc_columns = [col["name"] for col in inspector.get_columns("kycs")]

    if is_sqlite:
        with op.batch_alter_table("kycs", schema=None) as batch_op:
            if "fssai_license_image_url" in kyc_columns:
                batch_op.drop_column("fssai_license_image_url")
            if "shop_image_url" in kyc_columns:
                batch_op.drop_column("shop_image_url")
    else:
        if "fssai_license_image_url" in kyc_columns:
            op.drop_column("kycs", "fssai_license_image_url")
        if "shop_image_url" in kyc_columns:
            op.drop_column("kycs", "shop_image_url")

