"""add profile history table

Revision ID: 9e8d1b4c3d1f
Revises: 4a3a0c2f9b6a
Create Date: 2025-09-20 01:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9e8d1b4c3d1f"
down_revision: Union[str, Sequence[str], None] = "4a3a0c2f9b6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "profiles"


def upgrade() -> None:
    op.create_table(
        "profile_history",
        sa.Column("history_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("changed_by", sa.String(length=100), nullable=True),
        sa.Column("change_origin", sa.String(length=50), nullable=True),
        sa.Column("change_reason", sa.String(length=255), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("previous_snapshot", sa.JSON(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_profile_history_profile_id",
        "profile_history",
        ["profile_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_profile_history_profile_id", table_name="profile_history", schema=SCHEMA)
    op.drop_table("profile_history", schema=SCHEMA)
