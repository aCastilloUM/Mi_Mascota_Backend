"""move profiles objects to schema

Revision ID: 4a3a0c2f9b6a
Revises: 6983da7f8b4f
Create Date: 2025-09-19 21:40:00
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a3a0c2f9b6a"
down_revision: Union[str, Sequence[str], None] = "6983da7f8b4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "profiles"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    op.execute(f"ALTER TYPE profile_role SET SCHEMA {SCHEMA}")
    op.execute(f"ALTER TABLE profiles SET SCHEMA {SCHEMA}")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {SCHEMA}.profiles SET SCHEMA public")
    op.execute(f"ALTER TYPE {SCHEMA}.profile_role SET SCHEMA public")
