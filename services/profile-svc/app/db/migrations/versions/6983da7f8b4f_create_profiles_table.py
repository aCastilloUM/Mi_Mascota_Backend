"""create profiles table

Revision ID: 6983da7f8b4f
Revises: 015507ab3c0d
Create Date: 2025-09-18 00:03:32.346684
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6983da7f8b4f"
down_revision: Union[str, Sequence[str], None] = "015507ab3c0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),  # puede salir como sa.UUID
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.Enum("client", "provider", name="profile_role"), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("services", sa.JSON(), nullable=True),
        sa.Column("photo_url", sa.String(length=300), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("second_name", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("document_type", sa.String(length=20), nullable=True),
        sa.Column("document", sa.String(length=50), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("street", sa.String(length=120), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("apartment", sa.String(length=20), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        sa.UniqueConstraint("user_id", name="uq_profile_user_id"),
        sa.UniqueConstraint("email", name="uq_profiles_email"),
        sa.UniqueConstraint("document", name="uq_profiles_document"),
    )
    op.create_index("ix_profiles_city", "profiles", ["city"], unique=False)


def downgrade() -> None:
    # 1) borrar el índice (si no, la tabla se borra igual, pero es prolijo)
    op.drop_index("ix_profiles_city", table_name="profiles")

    # 2) borrar la tabla (esto elimina PK/UQs asociados)
    op.drop_table("profiles")

    # 3) borrar el tipo ENUM explícitamente (opcional pero recomendado)
    #    Hacerlo *después* de dropear la tabla, para no romper dependencias.
    op.execute("DROP TYPE IF EXISTS profile_role;")
