"""Add email verification and password reset tokens

Revision ID: 20251006_0002
Revises: 20250916_0001
Create Date: 2025-10-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251006_0002'
down_revision = '20250916_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar campos de email verification a users
    op.add_column('users', 
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        schema='auth'
    )
    op.add_column('users',
        sa.Column('email_verification_token', sa.String(255), nullable=True),
        schema='auth'
    )
    op.add_column('users',
        sa.Column('email_verification_sent_at', sa.DateTime(timezone=True), nullable=True),
        schema='auth'
    )
    
    # Agregar campos de password reset
    op.add_column('users',
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        schema='auth'
    )
    op.add_column('users',
        sa.Column('password_reset_sent_at', sa.DateTime(timezone=True), nullable=True),
        schema='auth'
    )
    
    # Agregar campo de failed login attempts para account locking
    op.add_column('users',
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        schema='auth'
    )
    op.add_column('users',
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        schema='auth'
    )
    
    # Índices para búsqueda rápida por tokens
    op.create_index(
        'ix_auth_users_email_verification_token',
        'users',
        ['email_verification_token'],
        unique=False,
        schema='auth'
    )
    op.create_index(
        'ix_auth_users_password_reset_token',
        'users',
        ['password_reset_token'],
        unique=False,
        schema='auth'
    )


def downgrade() -> None:
    # Remover índices
    op.drop_index('ix_auth_users_password_reset_token', table_name='users', schema='auth')
    op.drop_index('ix_auth_users_email_verification_token', table_name='users', schema='auth')
    
    # Remover columnas
    op.drop_column('users', 'locked_until', schema='auth')
    op.drop_column('users', 'failed_login_attempts', schema='auth')
    op.drop_column('users', 'password_reset_sent_at', schema='auth')
    op.drop_column('users', 'password_reset_token', schema='auth')
    op.drop_column('users', 'email_verification_sent_at', schema='auth')
    op.drop_column('users', 'email_verification_token', schema='auth')
    op.drop_column('users', 'email_verified', schema='auth')
