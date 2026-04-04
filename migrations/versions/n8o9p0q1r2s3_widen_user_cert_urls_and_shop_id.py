"""widen user certificate url columns; add shop and id document urls

Revision ID: n8o9p0q1r2s3
Revises: d5e7da037c91
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


revision = "n8o9p0q1r2s3"
down_revision = "d5e7da037c91"
branch_labels = None
depends_on = None


CERT_COLS = ("gst_certificate", "fssai_license", "udyam_registration", "trade_certificate")


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    user_cols = {c["name"] for c in inspector.get_columns("users")}

    if is_sqlite:
        with op.batch_alter_table("users", schema=None) as batch_op:
            for col in CERT_COLS:
                if col in user_cols:
                    batch_op.alter_column(
                        col,
                        existing_type=sa.String(length=255),
                        type_=sa.Text(),
                        existing_nullable=True,
                    )
            if "shop_photo_url" not in user_cols:
                batch_op.add_column(sa.Column("shop_photo_url", sa.Text(), nullable=True))
            if "user_id_document_url" not in user_cols:
                batch_op.add_column(sa.Column("user_id_document_url", sa.Text(), nullable=True))
    else:
        for col in CERT_COLS:
            if col in user_cols:
                op.alter_column(
                    "users",
                    col,
                    existing_type=sa.String(length=255),
                    type_=sa.Text(),
                    existing_nullable=True,
                )
        if "shop_photo_url" not in user_cols:
            op.add_column("users", sa.Column("shop_photo_url", sa.Text(), nullable=True))
        if "user_id_document_url" not in user_cols:
            op.add_column("users", sa.Column("user_id_document_url", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    user_cols = {c["name"] for c in inspector.get_columns("users")}

    if is_sqlite:
        with op.batch_alter_table("users", schema=None) as batch_op:
            if "user_id_document_url" in user_cols:
                batch_op.drop_column("user_id_document_url")
            if "shop_photo_url" in user_cols:
                batch_op.drop_column("shop_photo_url")
            for col in CERT_COLS:
                if col in user_cols:
                    batch_op.alter_column(
                        col,
                        existing_type=sa.Text(),
                        type_=sa.String(length=255),
                        existing_nullable=True,
                    )
    else:
        if "user_id_document_url" in user_cols:
            op.drop_column("users", "user_id_document_url")
        if "shop_photo_url" in user_cols:
            op.drop_column("users", "shop_photo_url")
        for col in CERT_COLS:
            if col in user_cols:
                op.alter_column(
                    "users",
                    col,
                    existing_type=sa.Text(),
                    type_=sa.String(length=255),
                    existing_nullable=True,
                )
