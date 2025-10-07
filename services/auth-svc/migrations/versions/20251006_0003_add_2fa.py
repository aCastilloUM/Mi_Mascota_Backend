"""Add 2FA TOTP support

Revision ID: 20251006_0003
Revises: 20251006_0002
Create Date: 2025-10-06 00:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251006_0003'
down_revision: Union[str, None] = '20251006_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 2FA TOTP fields to users table"""
    
    # Add 2FA fields
    op.add_column('users', 
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'),
        schema='auth'
    )
    
    op.add_column('users',
        sa.Column('two_factor_secret', sa.String(length=32), nullable=True),
        schema='auth'
    )
    
    op.add_column('users',
        sa.Column('two_factor_backup_codes', postgresql.ARRAY(sa.String()), nullable=True),
        schema='auth'
    )
    
    op.add_column('users',
        sa.Column('two_factor_enabled_at', sa.DateTime(timezone=True), nullable=True),
        schema='auth'
    )
    
    # Create index on two_factor_enabled for faster queries
    op.create_index(
        'ix_auth_users_two_factor_enabled',
        'users',
        ['two_factor_enabled'],
        schema='auth'
    )


def downgrade() -> None:
    """Remove 2FA TOTP fields from users table"""
    
    # Drop index
    op.drop_index('ix_auth_users_two_factor_enabled', table_name='users', schema='auth')
    
    # Drop columns
    op.drop_column('users', 'two_factor_enabled_at', schema='auth')
    op.drop_column('users', 'two_factor_backup_codes', schema='auth')
    op.drop_column('users', 'two_factor_secret', schema='auth')
    op.drop_column('users', 'two_factor_enabled', schema='auth')
